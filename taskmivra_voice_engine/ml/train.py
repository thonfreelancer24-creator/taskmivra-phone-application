"""Training entry point for TaskMivra-owned target-speaker weights."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from dataset import TaskMivraRightsGatedDataset
from model import TaskMivraTargetSpeakerNet


def si_sdr(est, target):
    est = est - est.mean(-1, keepdim=True)
    target = target - target.mean(-1, keepdim=True)
    scale = (est * target).sum(-1, keepdim=True) / (target.square().sum(-1, keepdim=True) + 1e-8)
    proj = scale * target
    noise = est - proj
    return 10 * torch.log10((proj.square().sum(-1) + 1e-8) / (noise.square().sum(-1) + 1e-8))


def spectral_loss(est, target):
    window = torch.hann_window(960, device=est.device, dtype=est.dtype)
    est_spec = torch.stft(est, 1024, 480, 960, window, return_complex=True)
    tgt_spec = torch.stft(target, 1024, 480, 960, window, return_complex=True)
    diff = (torch.log1p(10 * est_spec.abs()) - torch.log1p(10 * tgt_spec.abs())).abs()
    freqs = torch.linspace(0, 24000, diff.shape[-2], device=diff.device)
    weights = torch.ones_like(freqs)
    weights[(freqs >= 1000) & (freqs <= 8000)] = 1.6
    return (diff * weights[None, :, None]).mean()


def profile_margin_loss(model, mixture, target, positive_profile, negative_profile, has_negative):
    if has_negative.max().item() == 0:
        return mixture.new_tensor(0.0)

    # Output-level requirement: correct profile must reconstruct the target
    # more accurately than a competing profile.
    pos_est, _ = model(mixture, positive_profile)
    neg_est, _ = model(mixture, negative_profile)
    pos_score = si_sdr(pos_est, target)
    neg_score = si_sdr(neg_est, target)
    output_margin = torch.relu(1.5 - (pos_score - neg_score))

    # Embedding-level requirement: a target-speech segment must be closer to
    # its own enrolled profile than to the competing profile.
    target_emb = model.encode_profile(target)
    pos_emb = model.encode_profile(positive_profile)
    neg_emb = model.encode_profile(negative_profile)
    pos_distance = 1.0 - (target_emb * pos_emb).sum(dim=-1)
    neg_distance = 1.0 - (target_emb * neg_emb).sum(dim=-1)
    embedding_margin = torch.relu(0.35 + pos_distance - neg_distance)

    combined = output_margin + embedding_margin
    return (combined * has_negative).sum() / has_negative.sum().clamp_min(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--out", default="checkpoints")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--start-epoch", type=int, default=1)
    ap.add_argument("--resume", default=None, help="Optional TaskMivra checkpoint to continue from")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--segment", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--spectral-weight", type=float, default=1.8)
    ap.add_argument("--profile-weight", type=float, default=0.45)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    torch.manual_seed(1337)
    dataset = TaskMivraRightsGatedDataset(args.manifest, segment_seconds=args.segment)
    loader = DataLoader(dataset, batch_size=args.batch, shuffle=True, num_workers=0, drop_last=False)

    model = TaskMivraTargetSpeakerNet().to(args.device)
    if args.resume:
        checkpoint = torch.load(args.resume, map_location=args.device)
        model.load_state_dict(checkpoint["model"])

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for epoch in range(args.start_epoch, args.start_epoch + args.epochs):
        model.train()
        total_loss = 0.0
        total_si_sdr = 0.0
        total_profile = 0.0
        started = time.time()

        for batch in loader:
            mixture = batch["mixture"].to(args.device)
            target = batch["target"].to(args.device)
            profile = batch["profile"].to(args.device)
            negative_profile = batch["negative_profile"].to(args.device)
            has_negative = batch["has_negative"].to(args.device)

            estimate, mask = model(mixture, profile)
            score = si_sdr(estimate, target)
            p_loss = profile_margin_loss(
                model, mixture, target, profile, negative_profile, has_negative
            )
            loss = (
                -score.mean()
                + args.spectral_weight * spectral_loss(estimate, target)
                + args.profile_weight * p_loss
                + 0.003 * (mask[:, :, 1:] - mask[:, :, :-1]).abs().mean()
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            total_loss += float(loss.detach())
            total_si_sdr += float(score.mean().detach())
            total_profile += float(p_loss.detach())

        batches = max(1, len(loader))
        meta = {
            "epoch": epoch,
            "loss": total_loss / batches,
            "si_sdr": total_si_sdr / batches,
            "profile_margin_loss": total_profile / batches,
            "seconds": time.time() - started,
            "architecture": "TaskMivraTargetSpeakerNet-v0.4",
            "pretrained_weights": False,
            "resume_source": str(args.resume) if args.resume else None,
        }
        print(json.dumps(meta), flush=True)
        torch.save({"model": model.state_dict(), "meta": meta}, out / f"epoch-{epoch:02d}.pt")


if __name__ == "__main__":
    main()
