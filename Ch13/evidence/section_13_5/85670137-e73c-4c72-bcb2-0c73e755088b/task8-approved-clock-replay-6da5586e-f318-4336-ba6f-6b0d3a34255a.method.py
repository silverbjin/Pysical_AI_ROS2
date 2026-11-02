"""Closed original FAIL stays unchanged; compare approved assessor offline."""
import hashlib,importlib.util,json,sys,uuid
from pathlib import Path
root=Path(sys.argv[1]);source=Path('Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/clock_witness.py')
spec=importlib.util.spec_from_file_location('replay_clock_witness',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
raw=root/'original-clocks.jsonl';legacy=root/'continuous-clock-result.json'
before=hashlib.sha256(legacy.read_bytes()).hexdigest()
with raw.open() as stream:assessed=module.assess_measured_clock_witness(json.loads(line) for line in stream)
assert before==hashlib.sha256(legacy.read_bytes()).hexdigest()
data=dict(scope='offline_approved_rule_replay_not_new_engine_or_acceptance',
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
 legacy_result_sha256=before,legacy_result_unchanged=True,legacy_passed=json.loads(legacy.read_text())['passed'],
 measured_rate=assessed,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
output=root.parent/('task8-approved-clock-replay-'+str(uuid.uuid4())+'.json')
output.write_text(json.dumps(data,indent=2));output.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(output),legacy_passed=data['legacy_passed'],measured_rate=assessed),indent=2))
