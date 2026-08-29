"""Optional SpEx+ -> released 48 kHz MossFormer2 speech-SR candidate."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter, _plain_samples
from crystal_voice.audio import Audio, encode_wav
from crystal_voice.provenance import verify_sr_assets


class SpExPlusMossFormerSRAdapter(TargetSpeakerExtractor):
    name = "Direct 8 kHz SpEx+ -> MossFormer2_SR_48K candidate"
    version = "WSJ0-2mix SpEx+ + MossFormer2_SR_48K"
    sample_rate = 48_000

    def load(self) -> None:
        self.extractor = ClearerVoiceSpExPlusAdapter()
        self.extractor.load()
        home = Path(os.environ.get("CRYSTAL_VOICE_SR_HOME", "runtime/ClearerVoice-Studio-SR")).resolve()
        checkpoint_dir = Path(os.environ.get(
            "CRYSTAL_VOICE_SR_CHECKPOINT_DIR", "runtime/checkpoints/MossFormer2_SR_48K"
        )).resolve()
        if not home.is_dir():
            raise RuntimeError(
                "Optional MossFormer2_SR_48K runtime is missing. SpEx+ remains an isolation-only benchmark; "
                "do not present its 8 kHz output as final quality."
            )
        required = (
            checkpoint_dir / "last_best_checkpoint",
            checkpoint_dir / "last_best_checkpoint_m.pt",
            checkpoint_dir / "last_best_checkpoint_g.pt",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"MossFormer2_SR_48K inference assets are missing: {missing}; run scripts/install_macos.sh")
        if checkpoint_dir.parent.name != "checkpoints":
            raise RuntimeError(
                "CRYSTAL_VOICE_SR_CHECKPOINT_DIR must end in checkpoints/MossFormer2_SR_48K "
                "to match the released ClearVoice inference config"
            )

        for candidate in (home, home / "clearvoice"):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        module = importlib.import_module("clearvoice")
        clear_voice = getattr(module, "ClearVoice", None)
        if clear_voice is None:
            raise RuntimeError("SR checkout does not expose clearvoice.ClearVoice")

        # The released inference config uses checkpoint_dir: checkpoints/MossFormer2_SR_48K.
        # Construct ClearVoice from the parent of checkpoints so that relative path resolves
        # to our deterministic runtime assets, then immediately restore the caller's cwd.
        original_cwd = Path.cwd()
        try:
            os.chdir(checkpoint_dir.parent.parent)
            self.restorer = clear_voice(task="speech_super_resolution", model_names=["MossFormer2_SR_48K"])
        finally:
            os.chdir(original_cwd)
        self.sr_provenance_path = verify_sr_assets(checkpoint_dir)

    def enroll(self, reference: Audio) -> object:
        return self.extractor.enroll(reference)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        isolated = self.extractor.extract(mixture, profile)
        return self.restore(isolated)

    def restore(self, isolated: Extraction) -> Extraction:
        with tempfile.TemporaryDirectory(prefix="crystal-sr-") as directory:
            input_path = Path(directory) / "spex-48k.wav"
            input_path.write_bytes(encode_wav(isolated.audio))
            output = self.restorer(input_path=str(input_path), online_write=False)
        restored = Audio(_plain_samples(output), 48_000)
        return Extraction(restored, {
            **isolated.metadata,
            "post_processing": "MossFormer2_SR_48K candidate",
            "restoration_must_pass_identity_and_artifact_gates": True,
        })
