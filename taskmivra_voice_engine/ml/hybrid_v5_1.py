"""TaskMivra Voice Hybrid v5.1.

Phase-safe commercial candidate built around TaskMivra-owned v1.1 weights.
The locked Crystal Voice v0.4 baseline remains evaluation/listening reference only.
No benchmark code, weights, or generated outputs are used for training/distillation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from scipy.signal import istft as scipy_istft
from scipy.signal import resample_poly
from scipy.signal import stft as scipy_stft

from .fast_profile_v1_1 import TaskMivraFastProfileComplex

SAMPLE_RATE = 48_000


@dataclass(frozen=True)
class RouteDecision:
    route: str
    noise_flatness: float
    noise_ratio_db: float


def _profile_complex_mask(model, wave16: torch.Tensor, profile16: torch.Tensor) -> torch.Tensor:
    """Return v1.1 mask magnitude only; deliberately discard learned complex phase."""
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


class TaskMivraCrystalReferenceHybridV51:
    """Speech-safe hybrid denoiser. Input/output are mono float32 48 kHz arrays."""

    def __init__(self, checkpoint: dict, profile_48k: np.ndarray) -> None:
        self.model = TaskMivraFastProfileComplex()
        state = checkpoint["model"] if "model" in checkpoint else checkpoint
        self.model.load_state_dict(state)
        self.model.eval()
        profile = np.asarray(profile_48k, dtype=np.float32)
        if len(profile) < SAMPLE_RATE * 3:
            raise ValueError("voice profile must be at least 3 seconds")
        self.profile16 = torch.from_numpy(resample_poly(profile[: SAMPLE_RATE * 5], 1, 3).astype(np.float32))[None]

    @staticmethod
    def analyze_noise(x48: np.ndarray) -> RouteDecision:
        frequencies, _, spec = scipy_stft(
            x48,
            fs=SAMPLE_RATE,
            window="hann",
            nperseg=960,
            noverlap=480,
            nfft=1024,
            boundary="zeros",
            padded=True,
        )
        power = np.abs(spec) ** 2 + 1e-14
        band = (frequencies > 100) & (frequencies < 8000)
        noise_floor = np.percentile(power, 20, axis=1)
        flatness = float(
            np.exp(np.mean(np.log(noise_floor[band] + 1e-14)))
            / np.mean(noise_floor[band] + 1e-14)
        )
        ratio_db = float(
            10.0
            * np.log10(
                (power[band].mean() + 1e-14)
                / (noise_floor[band].mean() + 1e-14)
            )
        )
        if ratio_db >= 29.0:
            route = "clean-bypass"
        elif flatness >= 0.36 and ratio_db <= 15.5:
            route = "broadband-wiener"
        else:
            route = "owned-mask-phase-safe"
        return RouteDecision(route, flatness, ratio_db)

    def _owned_mask_phase_safe(self, x48: np.ndarray) -> np.ndarray:
        x16 = resample_poly(x48, 1, 3).astype(np.float32)
        with torch.inference_mode():
            gain = _profile_complex_mask(
                self.model, torch.from_numpy(x16)[None], self.profile16
            )[0].cpu().numpy()

        gain = np.clip(gain, 0.22, 1.0)
        smooth = np.empty_like(gain)
        smooth[:, 0] = gain[:, 0]
        for frame in range(1, gain.shape[1]):
            alpha = np.where(gain[:, frame] > smooth[:, frame - 1], 0.58, 0.18)
            smooth[:, frame] = smooth[:, frame - 1] + alpha * (
                gain[:, frame] - smooth[:, frame - 1]
            )
        smooth[1:-1] = 0.15 * smooth[:-2] + 0.70 * smooth[1:-1] + 0.15 * smooth[2:]
        smooth = 0.90 * smooth + 0.10

        # Matching 32 ms / 8 ms grid at 48 kHz. Only 0-8 kHz receives learned attenuation.
        # Above 8 kHz is untouched to preserve consonant/air detail.
        window48 = torch.hann_window(1536)
        mixture48 = torch.stft(
            torch.from_numpy(np.asarray(x48, dtype=np.float32)),
            1536,
            384,
            1536,
            window48,
            return_complex=True,
        )
        frames = min(mixture48.shape[1], smooth.shape[1])
        final_gain = torch.ones_like(mixture48.real)
        final_gain[:257, :frames] = torch.from_numpy(smooth[:, :frames])
        enhanced = mixture48 * final_gain
        return torch.istft(
            enhanced, 1536, 384, 1536, window48, length=len(x48)
        ).cpu().numpy().astype(np.float32)

    @staticmethod
    def _broadband_wiener(x48: np.ndarray) -> np.ndarray:
        frequencies, _, spec = scipy_stft(
            x48,
            fs=SAMPLE_RATE,
            window="hann",
            nperseg=960,
            noverlap=480,
            nfft=1024,
            boundary="zeros",
            padded=True,
        )
        power = (np.abs(spec) ** 2).astype(np.float64)
        noise = np.percentile(power, 20, axis=1, keepdims=True)
        noise[1:-1] = 0.2 * noise[:-2] + 0.6 * noise[1:-1] + 0.2 * noise[2:]
        gain = np.sqrt(np.maximum(1.0 - noise / (power + 1e-14), 0.35**2))
        gain[frequencies > 12000] = np.maximum(gain[frequencies > 12000], 0.80)

        smooth = np.empty_like(gain)
        smooth[:, 0] = gain[:, 0]
        for frame in range(1, gain.shape[1]):
            alpha = np.where(gain[:, frame] > smooth[:, frame - 1], 0.58, 0.20)
            smooth[:, frame] = smooth[:, frame - 1] + alpha * (
                gain[:, frame] - smooth[:, frame - 1]
            )
        smooth[1:-1] = 0.15 * smooth[:-2] + 0.70 * smooth[1:-1] + 0.15 * smooth[2:]
        _, output = scipy_istft(
            spec * smooth,
            fs=SAMPLE_RATE,
            window="hann",
            nperseg=960,
            noverlap=480,
            nfft=1024,
            input_onesided=True,
            boundary=True,
        )
        return output[: len(x48)].astype(np.float32)

    def process(self, x48: np.ndarray) -> tuple[np.ndarray, RouteDecision]:
        x = np.asarray(x48, dtype=np.float32)
        decision = self.analyze_noise(x)
        if decision.route == "clean-bypass":
            return x.copy(), decision
        if decision.route == "broadband-wiener":
            return self._broadband_wiener(x), decision
        return self._owned_mask_phase_safe(x), decision
