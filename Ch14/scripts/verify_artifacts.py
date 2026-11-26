"""Verify an Actions evidence ZIP without extracting or executing its contents."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def verify(path, expected_sha, expected_source):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha) or not re.fullmatch(r'[0-9a-f]{40}', expected_source):
        raise ValueError('expected immutable ZIP and source SHA required')
    with path.open('rb') as f:
        actual = hashlib.file_digest(f, 'sha256').hexdigest()
    if actual != expected_sha:
        raise ValueError('ZIP SHA256 mismatch')
    with ZipFile(path) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        if len(names) != len(set(names)) or any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts or '\\' in n for n in names):
            raise ValueError('unsafe or duplicate ZIP path')
        expected = {}
        for line in z.read('sha256sums.txt').decode('utf-8').splitlines():
            digest, name = line.split(maxsplit=1)
            name = name.removeprefix('./')
            if not re.fullmatch(r'[0-9a-f]{64}', digest) or name in expected or name == 'sha256sums.txt':
                raise ValueError('invalid manifest entry')
            expected[name] = digest
        if set(expected) != set(names) - {'sha256sums.txt'}:
            raise ValueError('manifest coverage mismatch')
        for name, digest in expected.items():
            with z.open(name) as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() != digest:
                    raise ValueError(f'internal SHA256 mismatch: {name}')
        source = z.read('source-sha.txt').decode('utf-8').strip()
        if source != expected_source:
            raise ValueError('source SHA mismatch')
        result = json.loads(z.read('result.json'))
    return {'integrity': 'PASS', 'zip_sha256': actual, 'source_sha': source,
            'internal_files_verified': len(expected), 'recorded_execution_result': result}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('artifact', type=Path)
    p.add_argument('--sha256', required=True)
    p.add_argument('--source-sha', required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.artifact, a.sha256, a.source_sha), indent=2))


if __name__ == '__main__':
    main()
