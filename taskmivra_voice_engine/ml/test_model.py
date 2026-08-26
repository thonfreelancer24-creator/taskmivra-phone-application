import json, tempfile
from pathlib import Path
import torch
from model import TaskMivraTargetSpeakerNet, FREQ_BINS
from rights import load_manifest

m=TaskMivraTargetSpeakerNet()
mixture=torch.randn(2,48000)*.02
profile=torch.randn(2,144000)*.02
with torch.no_grad():
    y,mask=m(mixture,profile)
assert y.shape==mixture.shape
assert mask.shape[1]==FREQ_BINS
assert torch.isfinite(y).all()
assert float(mask.min())>=0 and float(mask.max())<=1
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'m.jsonl'
    p.write_text(json.dumps({'target_clean':'a.wav','profile_clean':'b.wav','rights':{'target_clean':'taskmivra-owned','profile_clean':'taskmivra-owned'}})+'\n')
    assert len(load_manifest(p))==1
    p.write_text(json.dumps({'target_clean':'locked.wav','derived_from_benchmark_output':True,'rights':{'target_clean':'taskmivra-owned'}})+'\n')
    try: load_manifest(p); raise AssertionError('must reject benchmark output')
    except ValueError: pass
print('PASS: model forward + fail-closed rights gate')
