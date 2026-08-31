# Temporary MossFormer2 Fallback

**Approved pilot window:** August 31, 2026 through September 7, 2026

## Purpose
Use the commercially cleared `MossFormer2_SE_48K` enhancement component as a temporary quality fallback while the TaskMivra-owned voice engine is completed and validated.

## Hard boundaries
- This is temporary and must not become the permanent TaskMivra voice engine.
- WeSep, BSRNN-ECAPA, WeSpeaker, SpEx+, Krisp, and any other uncleared component remain prohibited.
- Only the exact `MossFormer2_SE_48K` path cleared in `taskmivra_voice_engine/LICENSE-INVENTORY.md` is permitted.
- Required Apache-2.0 license and attribution notices must remain with any distributed build containing this component.
- Do not describe MossFormer2 weights as TaskMivra-owned.
- Incoming/remote caller audio must bypass the voice engine.
- Physical microphone fail-safe must remain available.

## Replacement trigger
Replace this temporary fallback immediately after the TaskMivra-owned engine passes all of the following:
1. Target voice remains natural and intelligible.
2. TV/music/competing speaker suppression passes human listening.
3. No static, metallic, watery, robotic, choppy, slowed, or clipped speech.
4. Zero clipped samples.
5. Live-call streaming is stable with bounded buffering and no dropouts.
6. Real-time performance is acceptable on intended customer hardware.
7. Inbound and outbound TaskMivra Phone regression tests pass.

## Cutoff
September 7, 2026 is the planned one-week cutoff. If the TaskMivra-owned engine has not passed by then, the fallback may continue only after an explicit new internal approval and the same license/notice boundaries remain in force.
