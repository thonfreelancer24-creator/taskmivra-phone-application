"""TaskMivra Voice v1.1 profile-conditioned complex-mask inference architecture.
No pretrained voice weights are loaded by this module.
"""
from __future__ import annotations

import torch
from torch import nn

SAMPLE_RATE = 16000
N_FFT = 512
HOP_LENGTH = 128
WIN_LENGTH = 512
FREQ_BINS = 257


class TaskMivraFastProfileComplex(nn.Module):
    """Single-output target-speaker separator conditioned on an enrollment profile."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(FREQ_BINS * 2, 256),
            nn.GELU(),
            nn.Linear(256, 256),
            nn.GELU(),
            nn.Linear(256, FREQ_BINS * 2),
        )

    def forward(self, mixture_wave: torch.Tensor, profile_wave: torch.Tensor) -> torch.Tensor:
        window = torch.hann_window(WIN_LENGTH, device=mixture_wave.device)
        mix_spec = torch.stft(
            mixture_wave, N_FFT, HOP_LENGTH, WIN_LENGTH, window, return_complex=True
        )
        profile_mag = torch.stft(
            profile_wave, N_FFT, HOP_LENGTH, WIN_LENGTH, window, return_complex=True
        ).abs()
        profile_summary = torch.log1p(20.0 * profile_mag).mean(-1)
        mix_features = torch.log1p(20.0 * mix_spec.abs()).transpose(1, 2)
        profile_features = profile_summary[:, None, :].expand(-1, mix_features.shape[1], -1)
        output = self.net(torch.cat([mix_features, profile_features], dim=-1)).transpose(1, 2)
        mask_real = 2.0 * torch.tanh(output[:, :FREQ_BINS])
        mask_imag = 1.2 * torch.tanh(output[:, FREQ_BINS:])
        target_spec = mix_spec * torch.complex(mask_real, mask_imag)
        return torch.istft(
            target_spec,
            N_FFT,
            HOP_LENGTH,
            WIN_LENGTH,
            window,
            length=mixture_wave.shape[-1],
        )
