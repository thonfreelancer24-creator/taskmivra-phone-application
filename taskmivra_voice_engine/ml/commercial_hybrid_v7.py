"""TaskMivra Voice v7 commercial-safe hybrid processor.

Design rules:
- locked Crystal Voice v0.4 is a listening benchmark only;
- only TaskMivra-owned checkpoints are accepted here;
- original microphone phase is preserved by using learned masks as magnitude control;
- clean/quiet speech can bypass the suppression core exactly;
- RNNoise is an optional BSD-licensed environmental stage, with a deterministic
  SciPy Wiener fallback if the native library is unavailable;
- remote/call-receive audio is outside this module by design.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from scipy.signal import istft, resample_poly, stft

from .fast_profile_v1_1 import TaskMivraFastProfileComplex
from .rnnoise_adapter import RNNoiseProcessor, RNNoiseUnavailable

SAMPLE_RATE = 48_000


@dataclass(frozen=True)
class RouteDecision:
    route: str
    noise_flatness: float
    noise_ratio_db: float
    modulation_index: float
    rnnoise_available: bool


@dataclass(frozen=True)
class ProcessResult:
    audio: np.ndarray
    decision: RouteDecision
    core_bypassed: bool


def _load_owned_checkpoint(path: str | Path) -> TaskMivraFastProfileComplex:
    data = torch.load(path, map_location="cpu", weights_only=False)
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    if bool(meta.get("pretrained", False)) or bool(meta.get("pretrained_third_party", False)):
        raise RuntimeError("Refusing checkpoint marked as third-party/pretrained")
    state = data["model"] if isinstance(data, dict) and "model" in data else data
    model = TaskMivraFastProfileComplex()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def _mask_magnitude(model: TaskMivraFastProfileComplex, wave16: torch.Tensor, profile16: torch.Tensor) -> torch.Tensor:
    window = torch.hann_window(512, device=wave16.device, dtype=wave16.dtype)
    mix_spec = torch.stft(wave16, 512, 128, 512, window, return_complex=True)
    profile_mag = torch.stft(profile16, 512, 128, 512, window, return_complex=True).abs()
    profile_summary = torch.log1p(20.0 * profile_mag).mean(-1)
    mix_features = torch.log1p(20.0 * mix_spec.abs()).transpose(1, 2)
    profile_features = profile_summary[:, None, :].expand(-1, mix_features.shape[1], -1)
    output = model.net(torch.cat([mix_features, profile_features], dim=-1)).transpose(1, 2)
    mask_real = 2.0 * torch.tanh(output[:, :257])
    mask_imag = 1.2 * torch.tanh(output[:, 257:])
    return torch.sqrt(mask_real.square() + mask_imag.square())


def _smooth_gain(gain: np.ndarray, floor: float, wet: float) -> np.ndarray:
    gain = np.clip(gain, floor, 1.0)
    smooth = np.empty_like(gain)
    smooth[:, 0] = gain[:, 0]
    for frame in range(1, gain.shape[1]):
        alpha = np.where(gain[:, frame] > smooth[:, frame - 1], 0.62, 0.14)
        smooth[:, frame] = smooth[:, frame - 1] + alpha * (
            gain[:, frame] - smooth[:, frame - 1]
        )
    if smooth.shape[0] > 2:
        smooth[1:-1] = 0.12 * smooth[:-2] + 0.76 * smooth[1:-1] + 0.12 * smooth[2:]
    return (1.0 - wet) + wet * smooth


def _phase_safe_owned(model: TaskMivraFastProfileComplex, wave48: np.ndarray, profile48: np.ndarray, *, floor: float, wet: float) -> np.ndarray:
    wave16 = resample_poly(wave48, 1, 3).astype(np.float32)
    profile16 = resample_poly(profile48, 1, 3).astype(np.float32)
    with torch.inference_mode():
        gain = _mask_magnitude(
            model,
            torch.from_numpy(wave16)[None],
            torch.from_numpy(profile16)[None],
        )[0].cpu().numpy()
    gain = _smooth_gain(gain, floor, wet)

    window48 = torch.hann_window(1536)
    mixture48 = torch.stft(
        torch.from_numpy(np.asarray(wave48, dtype=np.float32)),
        1536,
        384,
        1536,
        window48,
        return_complex=True,
    )
    frames = min(mixture48.shape[1], gain.shape[1])
    final_gain = torch.ones_like(mixture48.real)
    final_gain[:257, :frames] = torch.from_numpy(gain[:, :frames])
    enhanced = mixture48 * final_gain
    return torch.istft(
        enhanced, 1536, 384, 1536, window48, length=len(wave48)
    ).cpu().numpy().astype(np.float32)


def _conservative_wiener(wave48: np.ndarray) -> np.ndarray:
    frequencies, _, spec = stft(
        wave48,
        fs=SAMPLE_RATE,
        window="hann",
        nperseg=960,
        noverlap=480,
        nfft=1024,
        boundary="zeros",
        padded=True,
    )
    power = np.abs(spec) ** 2 + 1e-14
    noise = np.percentile(power, 20, axis=1, keepdims=True)
    if noise.shape[0] > 2:
        noise[1:-1] = 0.2 * noise[:-2] + 0.6 * noise[1:-1] + 0.2 * noise[2:]
    gain = np.sqrt(np.maximum(1.0 - 0.90 * noise / power, 0.25**2))
    gain[frequencies > 12_000] = np.maximum(gain[frequencies > 12_000], 0.85)
    smooth = np.empty_like(gain)
    smooth[:, 0] = gain[:, 0]
    for frame in range(1, gain.shape[1]):
        alpha = np.where(gain[:, frame] > smooth[:, frame - 1], 0.65, 0.18)
        smooth[:, frame] = smooth[:, frame - 1] + alpha * (
            gain[:, frame] - smooth[:, frame - 1]
        )
    _, output = istft(
        spec * smooth,
        fs=SAMPLE_RATE,
        window="hann",
        nperseg=960,
        noverlap=480,
        nfft=1024,
        input_onesided=True,
        boundary=True,
    )
    return output[: len(wave48)].astype(np.float32)


def _analysis_features(wave48: np.ndarray) -> tuple[float, float, float]:
    frequencies, _, spec = stft(
        wave48,
        fs=SAMPLE_RATE,
        window="hann",
        nperseg=960,
        noverlap=480,
        nfft=1024,
        boundary=None,
        padded=False,
    )
    power = np.abs(spec) ** 2 + 1e-14
    band = (frequencies > 100) & (frequencies < 8_000)
    noise_floor = np.percentile(power, 20, axis=1)
    flatness = float(
        np.exp(np.mean(np.log(noise_floor[band] + 1e-14)))
        / (np.mean(noise_floor[band]) + 1e-14)
    )
    ratio_db = float(
        10.0
        * np.log10(
            (np.mean(power[band]) + 1e-14)
            / (np.mean(noise_floor[band]) + 1e-14)
        )
    )
    envelope = np.sqrt(np.mean(power[band], axis=0))
    modulation = float(np.std(envelope) / (np.mean(envelope) + 1e-8))
    return flatness, ratio_db, modulation


class TaskMivraCommercialHybridV7:
    """Standalone commercial-safe microphone processor pending human approval."""

    def __init__(
        self,
        environment_checkpoint: str | Path,
        speech_checkpoint: str | Path,
        profile_48k: np.ndarray,
        *,
        rnnoise_library: str | Path | None = None,
    ) -> None:
        profile = np.asarray(profile_48k, dtype=np.float32).reshape(-1)
        if profile.size < SAMPLE_RATE * 3:
            raise ValueError("Voice Profile must contain at least 3 seconds at 48 kHz")
        self.profile48 = profile[: SAMPLE_RATE * 5]
        self.environment_model = _load_owned_checkpoint(environment_checkpoint)
        self.speech_model = _load_owned_checkpoint(speech_checkpoint)
        try:
            self.rnnoise = RNNoiseProcessor(rnnoise_library)
        except RNNoiseUnavailable:
            self.rnnoise = None

    def _broadband(self, wave: np.ndarray) -> np.ndarray:
        if self.rnnoise is not None:
            try:
                return self.rnnoise.process(wave)[0]
            except Exception:
                pass
        return _conservative_wiener(wave)

    def process(self, wave_48k: np.ndarray, route_hint: str | None = None) -> ProcessResult:
        wave = np.asarray(wave_48k, dtype=np.float32).reshape(-1)
        flatness, ratio_db, modulation = _analysis_features(wave)
        if route_hint is None:
            if ratio_db >= 29.0:
                route = "clean-bypass"
            elif flatness >= 0.36 and ratio_db <= 15.5:
                route = "broadband-environment"
            elif modulation >= 0.95:
                route = "speech-tv"
            else:
                route = "general-owned"
        else:
            route = route_hint

        decision = RouteDecision(
            route=route,
            noise_flatness=flatness,
            noise_ratio_db=ratio_db,
            modulation_index=modulation,
            rnnoise_available=self.rnnoise is not None,
        )
        if route == "clean-bypass":
            return ProcessResult(wave.copy(), decision, True)

        broadband = self._broadband(wave)
        if route == "broadband-environment":
            owned = _phase_safe_owned(
                self.environment_model, wave, self.profile48, floor=0.14, wet=0.90
            )
            output = 0.20 * owned + 0.80 * broadband
        elif route == "speech-tv":
            owned = _phase_safe_owned(
                self.speech_model, wave, self.profile48, floor=0.22, wet=0.85
            )
            output = 0.80 * owned + 0.20 * broadband
        else:
            owned = _phase_safe_owned(
                self.environment_model, wave, self.profile48, floor=0.14, wet=0.90
            )
            output = 0.80 * owned + 0.20 * broadband
        return ProcessResult(np.clip(output, -0.999, 0.999).astype(np.float32), decision, False)
