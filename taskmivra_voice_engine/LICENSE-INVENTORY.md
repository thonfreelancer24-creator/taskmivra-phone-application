# License Inventory — TaskMivra Voice Engine commercial-safe branch

Production dependency gate: anything requiring separate commercial permission, a non-commercial/research-only grant, or unclear redistribution/model-weight rights is prohibited.

| Component | Version/source | License / rights basis | Commercial redistribution | Separate permission | Production status |
|---|---|---|---|---|---|
| TaskMivra Voice Engine source | current commercial-safe branch | TaskMivra proprietary project source | TaskMivra-controlled | No | INCLUDED |
| TaskMivra Voice Profile / speaker scoring | authored in this project | TaskMivra proprietary project source | TaskMivra-controlled | No | INCLUDED |
| TaskMivra owned voice checkpoints | TaskMivra training pipeline; rights-gated data only | TaskMivra-controlled resulting weights | TaskMivra-controlled | No | INCLUDED |
| PyTorch | 2.2.2 production pin | BSD-style license in upstream LICENSE; source/binary redistribution permitted with notices | Yes | No | PERMITTED |
| NumPy | 1.26.4 production pin | BSD-3-Clause-style upstream license; source/binary redistribution permitted with notices | Yes | No | PERMITTED |
| SciPy | 1.14.1 production pin | BSD-3-Clause upstream license; source/binary redistribution permitted with notices | Yes | No | PERMITTED |
| RNNoise | Xiph upstream commit `6cbfd53eb348a8d394e0757b4025c6ded34eb2b6` | BSD-3-Clause-style COPYING; source/binary redistribution and modification expressly permitted with notices | Yes | No | PERMITTED OPTIONAL ENVIRONMENTAL STAGE |
| ClearerVoice-Studio code | `modelscope/ClearerVoice-Studio` Apache-2.0 repository | Upstream repository includes Apache License 2.0 granting use, modification and redistribution subject to notice obligations | Yes, with Apache-2.0 notice obligations | No | PERMITTED OPTIONAL ENHANCEMENT RUNTIME |
| MossFormer2_SE_48K weights | `alibabasglab/MossFormer2_SE_48K`, model-card revision `eff8c97` / exact 48 kHz checkpoint | Official model repository identifies the model weights and declares `license: apache-2.0`; TaskMivra relies only on that published grant and preserves required notices | Yes, with Apache-2.0 notice obligations | No | PERMITTED OPTIONAL ENHANCEMENT RUNTIME; NOT TASKMIVRA-OWNED |
| Node.js runtime APIs used by WAV CLI/tests | Node.js >=20 | Runtime/tooling only; not a voice model | Subject to Node.js distribution terms if bundled | No special creator approval | TOOLING ONLY |
| JavaScript standard language/math APIs | ECMAScript runtime | General-purpose platform functionality | Platform/runtime terms | No | INCLUDED |
| Frozen Crystal Voice v0.4.0 | locked TaskMivra benchmark branch | Evaluation/listening benchmark only | Must not be bundled as a whole in commercial installer | N/A | REFERENCE ONLY |
| WeSep code / pretrained weights | external | Repository currently declares no accepted production license in this review; exact checkpoint rights remain uncleared | Not approved | Would require a separate completed dependency review | PROHIBITED |
| BSRNN-ECAPA / WeSpeaker weights | external | Checkpoint/training-data rights not accepted by this production gate | Not approved | Would require a separate completed dependency review | PROHIBITED |
| Other ClearerVoice models/weights | external | Only the exact `MossFormer2_SE_48K` code/weight path above is cleared by this review; no blanket approval is granted to other checkpoints | Not approved unless separately recorded | Separate review required | PROHIBITED BY DEFAULT |
| SpEx+ released checkpoints | external | Repository license does not by itself establish released checkpoint/training-data redistribution rights | Not approved | Would require a separate completed dependency review | PROHIBITED |
| Krisp technology/assets | external proprietary | No commercial redistribution grant relied upon | No | Yes / proprietary | PROHIBITED |

## Required distribution behavior

For every permissive dependency that ships in source or binary form, TaskMivra must include the applicable upstream copyright/license/notice text in the installer or accompanying third-party notices. TaskMivra must not use upstream project names or contributor names to imply endorsement.

For the cleared `MossFormer2_SE_48K` fallback, the distribution must include Apache License 2.0 and identify ClearerVoice-Studio / MossFormer2_SE_48K as a third-party component. TaskMivra must not describe those weights as TaskMivra-owned.

## Model/data boundary

Production TaskMivra-owned checkpoints may train only on material accepted by `ml/TRAINING_PROVENANCE.md`. The frozen Crystal Voice benchmark, WeSep/BSRNN/SpEx+ weights or outputs, real copyrighted television, and commercial music are not production training or distillation material unless a future review independently establishes explicit commercial model-training and redistribution rights.

The cleared `MossFormer2_SE_48K` checkpoint may be used as a runtime enhancement component under Apache-2.0, but its weights or outputs are not approved as TaskMivra-owned training/distillation material. This keeps the optional fallback legally and technically separate from the TaskMivra-owned model program.

## Live-call gate

Licensing clearance is not a latency or quality clearance. `MossFormer2_SE_48K` must not be inserted into the protected TaskMivra Phone outgoing media path until a local streaming wrapper demonstrates real-time factor <= 1.0 on the intended customer hardware, bounded buffering, no word cuts/static, zero clipping, and physical-microphone fail-safe behavior.

## Fail-closed rule

A new codec, library, SDK, model, checkpoint, corpus, binary, or cloud API is excluded from the production build until its exact version and rights basis are recorded here. Commercial use must already be granted by its license; TaskMivra will not depend on components that require asking the owner for special commercial permission.
