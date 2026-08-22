# Model provenance and integration status

No weights or upstream source code are redistributed by this milestone. The laboratory refuses to describe a model as ready unless the operator explicitly configures its local inference command. Each command must receive **mixture**, **reference**, and **output** paths; this mechanically prevents an accidentally unconditioned inference path.

| Adapter | Upstream | Code license reported by upstream | Checkpoint status | Milestone decision |
|---|---|---|---|---|
| ClearerVoice-Studio SpEx+ | `https://github.com/modelscope/ClearerVoice-Studio` | Apache-2.0 repository license | Not vendored; exact checkpoint terms/hash must be reviewed and recorded before use | Adapter implemented; evaluation blocked until a reviewed local checkout and checkpoint are supplied |
| WeSep reference-conditioned TSE | `https://github.com/wenet-e2e/wesep` | Apache-2.0 repository license | Not vendored; checkpoint-specific provenance/license must be reviewed | Independent candidate adapter implemented; evaluation blocked until a reviewed local checkout and checkpoint are supplied |
| Same-take diagnostic | TaskMivra milestone source | Project source terms | No weights | Plumbing only; explicitly ineligible for acceptance |

## Evidence and blocker

On 2026-08-22 the development environment could not reach GitHub: `git ls-remote` returned `CONNECT tunnel failed, response 403`. Consequently, downloading, hashing, or truthfully benchmarking either upstream checkpoint was impossible. The milestone records this as a blocker rather than silently substituting blind separation or claiming model quality.

Repository licensing does **not** automatically establish permission to redistribute every checkpoint or dataset derivative. Before evaluation, record the upstream commit, checkpoint filename, SHA-256, download page, model-card license, training-data provenance, framework versions, sample rate, and command below in a local evaluation record.

## Local command contract

Configure an upstream wrapper that accepts 16-bit mono WAV and writes an un-normalized 16-bit mono WAV at the input rate:

```bash
export CRYSTAL_VOICE_SPEX_COMMAND='python /reviewed/ClearerVoice-Studio/run_tse.py --mixture {mixture} --reference {reference} --output {output}'
# or
export CRYSTAL_VOICE_WESEP_COMMAND='python /reviewed/wesep/run_tse.py --mixture {mixture} --enroll {reference} --output {output}'
```

The quoted paths are injected by the adapter. A command missing any placeholder is rejected. Upstream wrappers differ across commits; do not copy the illustrative command without matching it to the reviewed checkout.

