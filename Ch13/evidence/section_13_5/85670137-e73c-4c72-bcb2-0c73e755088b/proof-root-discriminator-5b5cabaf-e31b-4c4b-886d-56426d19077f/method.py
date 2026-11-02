"""Read-only full G1 admission at the thin copy and exact canonical original."""
from dataclasses import replace
import hashlib,json,os,shutil,uuid
from pathlib import Path
from integrated_robot_navigation.carry_profile import CarryProfile,validate_profile
from integrated_robot_navigation.execution_contract import g2_execution_profile
from integrated_robot_navigation.model import compile_model

repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
copy=base/'native-g1-gazebo-65ce2fad-60da-41cf-b37b-8c3b9f9f706d'
storage=json.loads((copy/'storage-copy-ledger.json').read_text())
native=Path(storage['native_original']);assert native.stat().st_uid==os.getuid()
result=json.loads((native/'result.json').read_text())
profile_file=Path(next(x.split(':=',1)[1] for x in result['command'] if x.startswith('carry_profile:=')))
profile=CarryProfile(**json.loads(profile_file.read_text()))
model=compile_model(Path(result['scene']['robot']['path']).read_text())
expected=g2_execution_profile(result['scene'],result['execution_mode']['control_clock'])
rows=[]
for directory in (copy,native):
    path=directory/'result.json';raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    candidate=replace(profile,state='native_validated',native_evidence={'gazebo':dict(path=str(path),sha256=sha)})
    accepted,reason=validate_profile(candidate,model,'gazebo',execution_profile=expected)
    rows.append(dict(path=str(path),result_sha256=sha,accepted=accepted,reason=reason))
assert rows[0]['result_sha256']==rows[1]['result_sha256']
assert not rows[0]['accepted'] and rows[1]['accepted'],rows
root=base/('proof-root-discriminator-'+str(uuid.uuid4()));root.mkdir()
(root/'method.py').write_bytes(Path(__file__).read_bytes())
(root/'result.json').write_text(json.dumps(dict(scope='full_unchanged_validator_no_engine_no_admission_bypass',
    rows=rows,required_checks=len(result['required_checks']),execution_profile=expected),indent=2))
# Preserve the pre-engine rejection exactly, without inventing a reaped parent
# or relaxing export_closed's required residual inspection.
failed=native.parent/'native-g2-gazebo-9affb1fd-a39c-4473-a032-8d40b16d1ae8'
failure=json.loads((failed/'result.json').read_text())
assert failure['engine_started'] is False and failure['status']=='FAIL'
target=root/'preengine_rejection';target.mkdir();inventory={}
for name in ('result.json','teardown.json','source_manifest.json','install_manifest.json','error_traceback.txt'):
    path=failed/name
    if not path.is_file():continue
    raw=path.read_bytes();assert len(raw)<100000
    (target/name).write_bytes(raw);inventory[name]=dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
(target/'copy-ledger.json').write_text(json.dumps(dict(scope='preengine_failure_metadata_only_not_normal_reap',
    native_original=str(failed),files=inventory,original_verdict_unchanged=True),indent=2))
print(json.dumps(dict(directory=str(root),rows=rows,engine_started=False)),flush=True)
