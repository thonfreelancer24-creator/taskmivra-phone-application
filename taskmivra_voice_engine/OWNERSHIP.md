# Ownership Boundary

The commercial TaskMivra voice-processing core is designed so TaskMivra controls the value-producing implementation.

TaskMivra-controlled project assets currently include:

- streaming DSP design and source implementation
- proprietary DSP tuning and quality gates
- Voice Profile enrollment and derived representation
- profile-conditioned speaker scoring and suppression logic
- live microphone integration boundary and fail-safe behavior
- future TaskMivra model architecture/training pipeline/weights, if ML is added
- application and license control plane
- product UX and branding

The v0.2 Voice Profile stores derived local measurements; it does not retain raw enrollment PCM in the profile object. Product integration must continue to keep the profile local unless a later, explicitly reviewed design changes that rule.

Ordinary operating-system/runtime functionality and general mathematical concepts are not claimed as TaskMivra property. No third-party pretrained voice technology is permitted in the production core without a separately documented dependency review that already grants the required rights; the default is exclusion.

The frozen Crystal Voice v0.4.0 implementation is retained only as an internal output benchmark and must never be bundled with this project or a customer installer.
