# Ownership Boundary

The commercial TaskMivra voice-processing core is designed so TaskMivra controls the value-producing implementation.

TaskMivra-controlled project assets include:

- streaming DSP design and source implementation
- proprietary tuning and quality gates
- future Voice Profile implementation
- future TaskMivra model architecture/training pipeline/weights, if ML is added
- live microphone integration adapter
- application and license control plane
- product UX and branding

Ordinary operating-system/runtime functionality and general mathematical concepts are not claimed as TaskMivra property. No third-party pretrained voice technology is permitted in the production core without a separately documented dependency review that already grants the required rights; the default is exclusion.

The frozen Crystal Voice v0.4.0 implementation is retained only as an internal output benchmark and must never be bundled with this project or a customer installer.
