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
| Node.js runtime APIs used by WAV CLI/tests | Node.js >=20 | Runtime/tooling only; not a voice model | Subject to Node.js distribution terms if bundled | No special creator approval | TOOLING ONLY |
| JavaScript standard language/math APIs | ECMAScript runtime | General-purpose platform functionality | Platform/runtime terms | No | INCLUDED |
| Frozen Crystal Voice v0.4.0 | locked TaskMivra benchmark branch | Evaluation/listening benchmark only | Must not be bundled in commercial installer | N/A | REFERENCE ONLY |
| WeSep code / pretrained weights | external | Exact repository/checkpoint redistribution and training-data rights not accepted by this production gate | Not approved | Would require a separate completed dependency review | PROHIBITED |
| BSRNN-ECAPA / WeSpeaker weights | external | Checkpoint/training-data rights not accepted by this production gate | Not approved | Would require a separate completed dependency review | PROHIBITED |
| ClearerVoice / MossFormer code or weights | external | Checkpoint/training-data rights not accepted by this production gate | Not approved | Would require a separate completed dependency review | PROHIBITED |
| SpEx+ released checkpoints | external | Repository license does not by itself establish released checkpoint/training-data redistribution rights | Not approved | Would require a separate completed dependency review | PROHIBITED |
| Krisp technology/assets | external proprietary | No commercial redistribution grant relied upon | No | Yes / proprietary | PROHIBITED |

## Required distribution behavior

For every permissive dependency that ships in source or binary form, TaskMivra must include the applicable upstream copyright/license/notice text in the installer or accompanying third-party notices. TaskMivra must not use upstream project names or contributor names to imply endorsement.

## Model/data boundary

Production checkpoints may train only on material accepted by `ml/TRAINING_PROVENANCE.md`. The frozen Crystal Voice benchmark, WeSep/MossFormer/BSRNN/SpEx+ outputs and weights, real copyrighted television, and commercial music are not production training or distillation material unless a future review independently establishes explicit commercial model-training and redistribution rights.

## Fail-closed rule

A new codec, library, SDK, model, checkpoint, corpus, binary, or cloud API is excluded from the production build until its exact version and rights basis are recorded here. Commercial use must already be granted by its license; TaskMivra will not depend on components that require asking the owner for special commercial permission.
