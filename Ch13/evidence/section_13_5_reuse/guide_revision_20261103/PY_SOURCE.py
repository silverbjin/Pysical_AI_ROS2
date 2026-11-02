from pathlib import Path
import hashlib, json
root = Path.cwd()
frozen = json.loads((root/'Ch13/dependencies/section_13_5_reuse_acceptance_v3.json').read_text())
for row in frozen['files']:
    data = (root/row['path']).read_bytes()
    assert len(data) == row['bytes'], row['path']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
print('SOURCE_FREEZE_PASS', len(frozen['files']))