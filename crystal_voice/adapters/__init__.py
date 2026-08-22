from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.adapters.external import ClearerVoiceSpExPlusAdapter, WeSepAdapter

ADAPTERS = {
    "diagnostic": SameTakeDiagnosticAdapter,
    "spexplus": ClearerVoiceSpExPlusAdapter,
    "wesep": WeSepAdapter,
}

