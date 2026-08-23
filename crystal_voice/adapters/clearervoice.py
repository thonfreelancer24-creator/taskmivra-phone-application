"""Direct integration of the released 8 kHz ClearerVoice SpEx+ network.

This module intentionally does *not* use the ClearVoice inference facade: that
facade does not publish an audio-only SpEx+ model.  It loads the training
architecture and the released WSJ0-2mix checkpoint/configuration directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import Audio
from crystal_voice.provenance import verify_spex_assets
from crystal_voice.resample import resample


@dataclass(frozen=True)
class SpExProfile:
    samples_8k: tuple[float, ...]


def _plain_samples(value: Any) -> tuple[float, ...]:
    if isinstance(value, dict):
        for key in ("MossFormer2_SR_48K", "waveform", "output", "audio", "wav"):
            if key in value:
                return _plain_samples(value[key])
        if len(value) == 1:
            return _plain_samples(next(iter(value.values())))
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    if hasattr(value, "tolist"):
        value = value.tolist()
    while isinstance(value, (list, tuple)) and len(value) == 1 and not isinstance(value[0], (int, float)):
        value = value[0]
    if not isinstance(value, (list, tuple)):
        raise RuntimeError(f"SpEx+ returned unsupported {type(value).__name__} output")
    samples = tuple(float(sample) for sample in value)
    if not samples or not all(math.isfinite(sample) for sample in samples):
        raise RuntimeError("SpEx+ returned an empty or non-finite waveform")
    return samples


def _namespace(value: Any) -> Any:
    """Recursively preserve the released YAML's nested attribute contract."""
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


def _find_config_value(config: Any, key: str) -> Any:
    if isinstance(config, dict):
        if key in config:
            return config[key]
        for value in config.values():
            found = _find_config_value(value, key)
            if found is not None:
                return found
    return None


class ClearerVoiceSpExPlusAdapter(TargetSpeakerExtractor):
    name = "ClearerVoice-Studio direct SpEx+ WSJ0-2mix"
    version = "log_wsj0-2mix_speech_SpEx-plus_2spk"
    sample_rate = 8_000
    eligible_for_acceptance = False

    def load(self) -> None:
        root = Path(os.environ.get("CRYSTAL_VOICE_SPEX_HOME", "runtime/spex-plus")).resolve()
        architecture = Path(os.environ.get(
            "CRYSTAL_VOICE_SPEX_ARCHITECTURE",
            root / "ClearerVoice-Studio/train/target_speaker_extraction/models/SpEx_plus/SpEx_plus.py",
        ))
        networks_path = Path(os.environ.get(
            "CRYSTAL_VOICE_SPEX_NETWORKS",
            root / "ClearerVoice-Studio/train/target_speaker_extraction/networks.py",
        ))
        config_path = Path(os.environ.get(
            "CRYSTAL_VOICE_SPEX_CONFIG", root / "config_wsj0-2mix_speech_SpEx-plus_2spk.yaml"
        ))
        checkpoint_path = Path(os.environ.get("CRYSTAL_VOICE_SPEX_CHECKPOINT", root / "last_best_checkpoint.pt"))
        for path in (architecture, networks_path, config_path, checkpoint_path):
            if not path.is_file():
                raise RuntimeError(f"Required direct SpEx+ asset is missing: {path}; run scripts/install_macos.sh")

        yaml = importlib.import_module("yaml")
        torch = importlib.import_module("torch")
        config = yaml.safe_load(config_path.read_text())
        audio_sr, ref_sr = _find_config_value(config, "audio_sr"), _find_config_value(config, "ref_sr")
        if audio_sr != 8_000 or ref_sr != 8_000:
            raise RuntimeError(f"Released SpEx+ config must declare audio_sr/ref_sr 8000, got {audio_sr}/{ref_sr}")

        for import_root in (architecture.parent, *architecture.parents):
            if (import_root / "train").is_dir() or import_root == architecture.parent:
                if str(import_root) not in sys.path:
                    sys.path.insert(0, str(import_root))
        spec = importlib.util.spec_from_file_location(
            "train.target_speaker_extraction.networks", networks_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot import upstream network_wrapper from {networks_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        network_wrapper = getattr(module, "network_wrapper", None)
        if network_wrapper is None:
            raise RuntimeError("Upstream networks.py does not expose network_wrapper")
        args = _namespace(config)
        args.device = torch.device("cpu")
        model = network_wrapper(args)
        checkpoint = torch.load(str(checkpoint_path), map_location="cpu")
        if not isinstance(checkpoint, dict) or "model" not in checkpoint:
            raise RuntimeError("Released checkpoint must be a mapping containing checkpoint['model']")
        state = checkpoint["model"]
        if not isinstance(state, dict):
            raise RuntimeError("checkpoint['model'] is not a state dictionary")
        if state and all(key.startswith("module.") for key in state):
            state = {key.removeprefix("module."): value for key, value in state.items()}
        model.load_state_dict(state, strict=True)
        model.eval()
        self._torch, self._model, self._config = torch, model, config
        self.provenance_path = verify_spex_assets(architecture, networks_path, config_path, checkpoint_path)

    def enroll(self, reference: Audio) -> SpExProfile:
        if not 3.0 <= reference.duration <= 5.0:
            raise ValueError("Target Voice Profile must be 3–5 seconds")
        return SpExProfile(resample(reference, self.sample_rate).samples)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        if not isinstance(profile, SpExProfile):
            raise TypeError("SpEx+ requires an enrolled reference profile")
        converted = resample(mixture, self.sample_rate)
        mix = self._torch.tensor(converted.samples, dtype=self._torch.float32).unsqueeze(0)
        reference = self._torch.tensor(profile.samples_8k, dtype=self._torch.float32).unsqueeze(0)
        aux_len = self._torch.tensor([len(profile.samples_8k)], dtype=self._torch.long)
        speakers = self._torch.tensor([-1], dtype=self._torch.long)
        with self._torch.inference_mode():
            output = self._model(mix, (reference, aux_len, speakers))
        if isinstance(output, dict):
            preferred = [output[key] for key in ("waveform", "estimated", "output", "speech") if key in output]
            candidates = preferred or list(output.values())
        else:
            candidates = output if isinstance(output, (tuple, list)) else (output,)
        waveform = None
        for candidate in candidates:
            if hasattr(candidate, "numel") and candidate.numel() >= len(converted.samples) * 0.9:
                waveform = candidate
                break
        if waveform is None:
            raise RuntimeError("SpEx+ output did not contain a full-duration extracted waveform")
        extracted = Audio(_plain_samples(waveform), self.sample_rate)
        restored = resample(extracted, mixture.sample_rate)
        return Extraction(restored, {
            "conditioned_by_reference": True,
            "model_sample_rate": 8_000,
            "input_sample_rate": mixture.sample_rate,
            "resampler": "48-tap Hann-windowed sinc, 94% Nyquist cutoff",
            "post_processing": "none",
            "quality_role": "isolation benchmark only; 8 kHz is not final Crystal Voice bandwidth",
        })
