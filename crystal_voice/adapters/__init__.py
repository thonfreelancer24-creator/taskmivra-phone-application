from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.adapters.external import WeSepAdapter
from crystal_voice.adapters.restoration import SpExPlusMossFormerSRAdapter

ADAPTERS = {
    "diagnostic": SameTakeDiagnosticAdapter,
    "spexplus": ClearerVoiceSpExPlusAdapter,
    "spexplus-sr": SpExPlusMossFormerSRAdapter,
    "wesep": WeSepAdapter,
}
