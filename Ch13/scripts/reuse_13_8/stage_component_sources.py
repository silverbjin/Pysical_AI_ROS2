"""Hash-checked native test snapshot; never copies models or engine evidence."""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_system_validation'))
    from ch13_system_validation.tools import validate_build
    build=validate_build(os.environ.get('CH13_REUSE_BUILD','/home/jinho/ch13_reuse_13_8_build'))
    staging=build/('component_source_'+uuid.uuid4().hex);staging.mkdir()
    target=staging/'repo';target.mkdir()
    spec=importlib.util.spec_from_file_location('validation_source_freeze',root/'Ch13/scripts/reuse_13_8/freeze_runtime.py')
    freeze=importlib.util.module_from_spec(spec);spec.loader.exec_module(freeze)
    sources=freeze.sources()
    fixtures={}
    for name in ('Ch13/evidence/section_13_6_reuse/2ece9bb8-1960-44de-b92b-31325ae5dc18/run/moveit_probe.json',):
        fixtures[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    for name,digest in {**sources,**fixtures}.items():
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/name,destination)
        assert hashlib.sha256(destination.read_bytes()).hexdigest()==digest,name
    (staging/'upstream-iit-locomanipulation-d010212').symlink_to(root.parent/'upstream-iit-locomanipulation-d010212',target_is_directory=True)
    (staging/'ch13_reuse_engine.lock').symlink_to(root.parent/'ch13_reuse_engine.lock')
    (staging/'snapshot.json').write_text(json.dumps(dict(source_root=str(root),files=sources,read_only_fixtures=fixtures),indent=2)+'\n')
    print('NATIVE_TEST_SOURCE',target,flush=True)
    with (staging/'tests.log').open('w') as log:
        result=subprocess.run(['bash',str(target/'Ch13/scripts/reuse_13_8/env.sh'),'-u',
            str(target/'Ch13/scripts/reuse_13_8/run_components.py'),*sys.argv[1:]],cwd=target,stdout=log,stderr=subprocess.STDOUT)
    print((staging/'tests.log').read_text()[-12000:]);return result.returncode


if __name__=='__main__':sys.exit(main())
