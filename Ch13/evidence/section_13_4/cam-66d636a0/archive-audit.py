"""Byte-level archive audit, deliberately separate from failed native acceptance."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()/'Ch13/scripts'))
from verify_vision_13_4 import file_digest

repo = Path.cwd().resolve()
base = repo/'Ch13/evidence/section_13_4'
names = ('camera-ownership-35954ef5-3ada-46e9-886b-c5e1f6d4a5a4',
         'cam-edfdbd00', 'cam-66d636a0')
destination = base/'cam-66d636a0/archive-index.json'
rows, references = [], 0
for name in names:
    for path in sorted((base/name).rglob('*')):
        if not path.is_file() or path == destination:
            continue
        assert path.resolve().is_relative_to((base/name).resolve())
        rows.append(dict(path=str(path.relative_to(repo)), size=path.stat().st_size,
                         sha256=file_digest(path)))
        if path.name == 'result.json':
            value = json.loads(path.read_text())
            for artifact in value.get('artifacts', []):
                source = (Path(value['artifact_root'])/artifact['path']).resolve(strict=True)
                assert source.is_relative_to(Path(value['artifact_root']).resolve())
                assert source.stat().st_size == artifact['size']
                assert file_digest(source) == artifact['sha256']
                references += 1
report = dict(integrity='PASS', native_acceptance='FAIL', files=len(rows),
              registered_references_verified=references,
              note='All listed bytes checked; this does not convert failed/partial runs into acceptance.',
              entries=rows)
destination.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({key: value for key, value in report.items() if key != 'entries'}))
