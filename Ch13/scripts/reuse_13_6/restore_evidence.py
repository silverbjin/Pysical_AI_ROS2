"""Restore verified archive members in their case folder; never overwrite data."""
import hashlib
import json
import sys
import tarfile
from pathlib import Path,PurePosixPath


def digest(data):return hashlib.sha256(data).hexdigest()


def restore(folder):
    folder=Path(folder).resolve();manifest=json.loads((folder/'raw_manifest.json').read_text())
    archive=folder/manifest['archive'];assert digest(archive.read_bytes())==manifest['archive_sha256']
    expected={entry['path']:entry for entry in manifest['files'] if entry['published']};restored=0;existing=0
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();assert len(members)==len(expected)
        assert len({member.name for member in members})==len(members),'duplicate archive path'
        for member in members:
            relative=PurePosixPath(member.name)
            assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
            target=(folder/str(relative)).resolve();assert target.is_relative_to(folder)
            entry=expected[member.name];data=tar.extractfile(member).read()
            assert len(data)==entry['bytes'] and digest(data)==entry['sha256'],member.name
            if target.exists():
                assert target.is_file() and digest(target.read_bytes())==entry['sha256'],'existing evidence differs; will not overwrite'
                existing+=1
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as output:output.write(data)
                restored+=1
    return dict(result='PASS',case=folder.name,restored=restored,existing_unchanged=existing)


if __name__=='__main__':print(json.dumps([restore(folder) for folder in sys.argv[1:]],indent=2))
