"""Rights-gated audio dataset for TaskMivra-owned target-speaker training."""
from __future__ import annotations
import random
import wave

import numpy as np
import torch
from torch.utils.data import Dataset

from rights import load_manifest

SAMPLE_RATE = 48000


def read_pcm16_mono(path):
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != SAMPLE_RATE or w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 48 kHz PCM16 WAV")
        channels = w.getnchannels()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32).reshape(-1, channels).mean(1) / 32768.0
    return torch.from_numpy(x.copy())


def tile_to_length(x, n):
    if len(x) >= n:
        return x
    return x.repeat((n + len(x) - 1) // len(x))


def crop_or_tile(x, n, rng):
    x = tile_to_length(x, n)
    start = 0 if len(x) == n else rng.randrange(0, len(x) - n + 1)
    return x[start:start + n].clone()


def rms(x):
    return x.square().mean().sqrt().clamp_min(1e-6)


def mix_at_snr(target, other, snr_db):
    scale = (rms(target) / (rms(other) * 10 ** (snr_db / 20))).clamp(max=10)
    return target + other * scale


class TaskMivraRightsGatedDataset(Dataset):
    """Training rows may include an explicit negative profile for speaker-contrast learning."""

    def __init__(self, manifest_path, segment_seconds=2.0, profile_seconds=3.5, seed=1337):
        self.rows = load_manifest(manifest_path)
        self.seg_n = int(segment_seconds * SAMPLE_RATE)
        self.prof_n = int(profile_seconds * SAMPLE_RATE)
        self.seed = seed

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        crop_seed = int(row.get("crop_seed", index))
        rng = random.Random(self.seed + crop_seed * 7919)

        target_full = read_pcm16_mono(row["target_clean"])

        if row.get("mixture"):
            mixture_full = read_pcm16_mono(row["mixture"])
            aligned_n = min(len(mixture_full), len(target_full))
            mixture_full = tile_to_length(mixture_full[:aligned_n], self.seg_n)
            target_full = tile_to_length(target_full[:aligned_n], self.seg_n)
            available = min(len(mixture_full), len(target_full))
            start = 0 if available == self.seg_n else rng.randrange(0, available - self.seg_n + 1)
            mixture = mixture_full[start:start + self.seg_n].clone()
            target = target_full[start:start + self.seg_n].clone()
        else:
            target = crop_or_tile(target_full, self.seg_n, rng)
            mixture = target.clone()
            if row.get("interference"):
                other = crop_or_tile(read_pcm16_mono(row["interference"]), self.seg_n, rng)
                mixture = mix_at_snr(mixture, other, rng.uniform(-5, 6))
            if row.get("noise"):
                noise = crop_or_tile(read_pcm16_mono(row["noise"]), self.seg_n, rng)
                mixture = mix_at_snr(mixture, noise, rng.uniform(-2, 12))
            peak = mixture.abs().max().clamp_min(1.0)
            mixture = mixture / peak

        profile = crop_or_tile(read_pcm16_mono(row["profile_clean"]), self.prof_n, rng)
        negative_path = row.get("negative_profile_clean")
        if negative_path:
            negative_profile = crop_or_tile(read_pcm16_mono(negative_path), self.prof_n, rng)
            has_negative = torch.tensor(1.0, dtype=torch.float32)
        else:
            negative_profile = profile.clone()
            has_negative = torch.tensor(0.0, dtype=torch.float32)

        return {
            "mixture": mixture,
            "target": target,
            "profile": profile,
            "negative_profile": negative_profile,
            "has_negative": has_negative,
        }
