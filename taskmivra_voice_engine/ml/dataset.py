"""Rights-gated audio mixture dataset for TaskMivra-owned target-speaker training."""
from __future__ import annotations
import random, wave
import numpy as np
import torch
from torch.utils.data import Dataset
from rights import load_manifest

SAMPLE_RATE=48000

def read_pcm16_mono(path):
    with wave.open(str(path),'rb') as w:
        if w.getframerate()!=SAMPLE_RATE or w.getsampwidth()!=2:
            raise ValueError(f'{path}: expected 48 kHz PCM16 WAV')
        ch=w.getnchannels(); raw=w.readframes(w.getnframes())
    x=np.frombuffer(raw,dtype='<i2').astype(np.float32).reshape(-1,ch).mean(1)/32768.0
    return torch.from_numpy(x.copy())

def crop_or_tile(x,n,rng):
    if len(x)<n: x=x.repeat((n+len(x)-1)//len(x))
    start=0 if len(x)==n else rng.randrange(0,len(x)-n+1)
    return x[start:start+n].clone()

def rms(x): return x.square().mean().sqrt().clamp_min(1e-6)
def mix_at_snr(target,other,snr_db):
    scale=(rms(target)/(rms(other)*10**(snr_db/20))).clamp(max=10)
    return target+other*scale

class TaskMivraRightsGatedDataset(Dataset):
    def __init__(self,manifest_path,segment_seconds=2.0,profile_seconds=3.5,seed=1337):
        self.rows=load_manifest(manifest_path); self.seg_n=int(segment_seconds*SAMPLE_RATE); self.prof_n=int(profile_seconds*SAMPLE_RATE); self.seed=seed
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        row=self.rows[index]; rng=random.Random(self.seed+index)
        target=crop_or_tile(read_pcm16_mono(row['target_clean']),self.seg_n,rng)
        profile=crop_or_tile(read_pcm16_mono(row['profile_clean']),self.prof_n,rng)
        mixture=target.clone()
        if row.get('interference'):
            other=crop_or_tile(read_pcm16_mono(row['interference']),self.seg_n,rng); mixture=mix_at_snr(mixture,other,rng.uniform(-3,8))
        if row.get('noise'):
            noise=crop_or_tile(read_pcm16_mono(row['noise']),self.seg_n,rng); mixture=mix_at_snr(mixture,noise,rng.uniform(0,15))
        peak=mixture.abs().max().clamp_min(1.0); mixture=mixture/peak
        return {'mixture':mixture,'target':target,'profile':profile}
