"""Exact two-wheel optional profile validation, without CPU wheelhouse assumptions."""
import argparse
import hashlib
import json
import re
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

EXPECTED = {'openvino', 'openvino-telemetry'}


def normalize(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def verify(lock, directory):
    locked = {}
    for line in lock.read_text().splitlines():
        m = re.fullmatch(r'([\w.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})', line)
        if not m:
            raise ValueError('invalid optional lock row')
        key = normalize(m[1])
        if key in locked:
            raise ValueError('duplicate lock name')
        locked[key] = (m[2], m[3])
    if set(locked) != EXPECTED:
        raise ValueError('unexpected OpenVINO profile')
    found = {}
    for path in sorted(directory.glob('*.whl')):
        if path.is_symlink():
            raise ValueError('symlink wheel')
        with ZipFile(path) as z:
            roots = [n for n in z.namelist() if n.endswith('.dist-info/METADATA') and n.count('/') == 1]
            if len(roots) != 1:
                raise ValueError('invalid wheel metadata')
            meta = BytesParser().parsebytes(z.read(roots[0]))
        key = normalize(str(meta['Name']))
        with path.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
        version = str(meta['Version'])
        if key in found or locked.get(key) != (version, sha):
            raise ValueError('optional wheel name/version/hash mismatch: ' + path.name)
        found[key] = {'wheel': path.name, 'version': version, 'sha256': sha,
                      'requires_dist': [str(r) for r in meta.get_all('Requires-Dist', [])],
                      'requires_python': str(meta.get('Requires-Python') or ''),
                      'license': str(meta.get('License-Expression') or meta.get('License') or '')}
    if set(found) != EXPECTED:
        raise ValueError('missing optional wheel')
    return {'status':'PASS','wheels':found}


def main():
    p=argparse.ArgumentParser();p.add_argument('lock',type=Path);p.add_argument('wheelhouse',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();result=verify(a.lock,a.wheelhouse)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('OPENVINO_WHEEL_HASH_PASS',len(result['wheels']))

if __name__=='__main__':main()
