"""Retain the failed v5 legacy run; verify only the affected probe supplement."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
from verify_vision_13_4 import source_snapshot, file_digest
from verify_all_13_4 import audit_installed_paths

base = Path(os.environ['CH13_EGL_EVIDENCE'])
original = json.loads((base/'final-v5/frozen-source.json').read_text())
root = base/'legacy-clock-final'
root.mkdir()
prefix = Path(os.environ['CH13_EGL_INSTALL'])

def installed():
    return {str(p.relative_to(prefix)): file_digest(p) for p in sorted(prefix.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}

snapshot = source_snapshot(Path.cwd())
changed = {p for p, digest in snapshot['files'].items()
           if original['snapshot']['files'].get(p) != digest}
assert changed == {'Ch13/scripts/verify_architecture_13_3.py',
                   'Ch13/tests/test_architecture_probe_time.py'}, changed
assert original['snapshot']['files'].keys() <= snapshot['files'].keys()
assert installed() == original['installed']
manifest = dict(batch_uuid=str(uuid.uuid4()), snapshot=snapshot, installed=installed(),
    changed_from_final_v5=sorted(changed), installation_audit=audit_installed_paths(prefix, Path.cwd()),
    rationale='Only the synthetic 13.3 probe and its regression changed; runtime/engine '
              'and 22 native trial sources/installations remain byte-identical. The failed '
              'final-v5 legacy trial is retained and not counted as a success.')
(root/'frozen-source.json').write_text(json.dumps(manifest, indent=2)+'\n')
for p, digest in snapshot['files'].items():
    data = Path(p).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
    target = root/'source_archive'/p
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
os.environ['CH13_EGL_EVIDENCE'] = str(root)
exec(compile(Path('Ch13/evidence/section_13_4/egl-424240ff/workflow/legacy.py').read_text(),
             'legacy.py', 'exec'), {'__name__': '__legacy_clock_final__'})
assert source_snapshot(Path.cwd())['files'] == snapshot['files']
assert installed() == original['installed']
(root/'after-audit.json').write_text(json.dumps(dict(status='PASS',
    source_files=len(snapshot['files']), installed_files=len(original['installed']),
    installation_audit=audit_installed_paths(prefix, Path.cwd())), indent=2)+'\n')
