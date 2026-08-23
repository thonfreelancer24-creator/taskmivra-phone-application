from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.adapters.external import WeSepAdapter

ADAPTERS = {
    "diagnostic": SameTakeDiagnosticAdapter,
    "spexplus": ClearerVoiceSpExPlusAdapter,
    "wesep": WeSepAdapter,
}
