"""TaskMivra-owned target-speaker model architecture. No pretrained weights."""
from __future__ import annotations
import torch
from torch import nn

SAMPLE_RATE = 48000
N_FFT = 1024
WIN_LENGTH = 960
HOP_LENGTH = 480
FREQ_BINS = N_FFT // 2 + 1


def analysis_stft(wave: torch.Tensor) -> torch.Tensor:
    window = torch.hann_window(WIN_LENGTH, device=wave.device, dtype=wave.dtype)
    return torch.stft(wave, n_fft=N_FFT, hop_length=HOP_LENGTH, win_length=WIN_LENGTH,
                      window=window, center=True, return_complex=True)


def mix_features(spec: torch.Tensor) -> torch.Tensor:
    """Per-frame normalization for the mixture path."""
    mag = spec.abs().transpose(1, 2)
    feat = torch.log1p(30.0 * mag)
    mean = feat.mean(dim=-1, keepdim=True)
    std = feat.std(dim=-1, keepdim=True).clamp_min(1e-4)
    return (feat - mean) / std


def profile_features(spec: torch.Tensor) -> torch.Tensor:
    """Speaker-preserving profile features.

    Do not normalize each frame across frequency here: that can erase the
    spectral-envelope/formant information needed to distinguish speakers.
    """
    mag = spec.abs().transpose(1, 2)
    feat = torch.log1p(30.0 * mag)
    mean = feat.mean(dim=(1, 2), keepdim=True)
    std = feat.std(dim=(1, 2), keepdim=True).clamp_min(1e-4)
    return (feat - mean) / std


class TaskMivraProfileEncoder(nn.Module):
    def __init__(self, embedding_dim: int = 96):
        super().__init__()
        self.input = nn.Sequential(nn.Linear(FREQ_BINS, 160), nn.GELU(), nn.LayerNorm(160))
        self.temporal = nn.GRU(160, 160, num_layers=1, batch_first=True, bidirectional=False)
        self.output = nn.Sequential(nn.Linear(320, 160), nn.GELU(), nn.Linear(160, embedding_dim))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        x = self.input(features)
        x, _ = self.temporal(x)
        pooled = torch.cat([x.mean(dim=1), x.std(dim=1)], dim=-1)
        emb = self.output(pooled)
        return nn.functional.normalize(emb, dim=-1)


class TaskMivraCausalSeparator(nn.Module):
    def __init__(self, embedding_dim: int = 96, hidden_dim: int = 256, layers: int = 2):
        super().__init__()
        self.mix_input = nn.Sequential(nn.Linear(FREQ_BINS, 192), nn.GELU(), nn.LayerNorm(192))
        self.condition = nn.Sequential(nn.Linear(192 + embedding_dim, hidden_dim), nn.GELU(), nn.LayerNorm(hidden_dim))
        self.recurrent = nn.GRU(hidden_dim, hidden_dim, num_layers=layers, batch_first=True)
        self.mask_head = nn.Sequential(nn.Linear(hidden_dim, 256), nn.GELU(), nn.Linear(256, FREQ_BINS))

    def forward(self, features: torch.Tensor, profile_embedding: torch.Tensor,
                state: torch.Tensor | None = None):
        x = self.mix_input(features)
        p = profile_embedding[:, None, :].expand(-1, x.shape[1], -1)
        x = self.condition(torch.cat([x, p], dim=-1))
        x, state = self.recurrent(x, state)
        mask = torch.sigmoid(self.mask_head(x))
        return mask, state


class TaskMivraTargetSpeakerNet(nn.Module):
    def __init__(self, embedding_dim: int = 96):
        super().__init__()
        self.profile_encoder = TaskMivraProfileEncoder(embedding_dim)
        self.separator = TaskMivraCausalSeparator(embedding_dim)

    def encode_profile(self, profile_wave: torch.Tensor) -> torch.Tensor:
        return self.profile_encoder(profile_features(analysis_stft(profile_wave)))

    def forward(self, mixture_wave: torch.Tensor, profile_wave: torch.Tensor):
        mix_spec = analysis_stft(mixture_wave)
        embedding = self.encode_profile(profile_wave)
        mask, _ = self.separator(mix_features(mix_spec), embedding)
        mask = mask.transpose(1, 2)
        target_spec = mix_spec * mask
        window = torch.hann_window(WIN_LENGTH, device=mixture_wave.device, dtype=mixture_wave.dtype)
        estimate = torch.istft(target_spec, n_fft=N_FFT, hop_length=HOP_LENGTH,
                               win_length=WIN_LENGTH, window=window, center=True,
                               length=mixture_wave.shape[-1])
        return estimate, mask
