python3 - <<'PY_ASSETS'
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from urllib.parse import quote
import hashlib, json
repo = Path.cwd().resolve()
lock = json.loads((repo/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())
target = repo.parent/'upstream-iit-locomanipulation-d010212'
existing = target.exists()
if not existing:
    target.mkdir()
base = 'https://raw.githubusercontent.com/iit-DLSLab/locomanipulation-teleop-isaaclab/'
for row in lock['files']:
    rel = PurePosixPath(row['path'])
    assert not rel.is_absolute() and '..' not in rel.parts
    destination = target.joinpath(*rel.parts)
    if existing:
        assert destination.is_file(), f'기존 폴더에 파일 누락: {rel}'
        data = destination.read_bytes()
    else:
        with urlopen(base+lock['upstream']['commit']+'/'+quote(str(rel), safe='/'), timeout=60) as response:
            data = response.read(row['bytes']+1)
        assert len(data) == row['bytes'], str(rel)
        assert hashlib.sha256(data).hexdigest() == row['sha256'], str(rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(data)
    assert len(data) == row['bytes'], str(rel)
    assert hashlib.sha256(data).hexdigest() == row['sha256'], str(rel)
print('ASSET_HASH_PASS', len(lock['files']), target)
PY_ASSETS
