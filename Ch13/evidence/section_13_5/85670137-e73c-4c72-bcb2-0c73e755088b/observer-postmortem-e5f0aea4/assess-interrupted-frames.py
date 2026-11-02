"""Derived postmortem; cannot promote an incomplete original run to PASS."""
import json,sys,time,uuid
from pathlib import Path
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'Ch13/scripts'))
from split_observer_13_5 import _load_recording,_digest
from verify_navigation_13_5 import assess_frames,operational_frames
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
original=native/'native-g2-mujoco-e5f0aea4-bbea-427d-8d25-f020bfbe78fd'
target=native/('interrupted-frames-assessment-'+str(uuid.uuid4()));target.mkdir()
print('ASSESSMENT',target,flush=True)
started=time.monotonic();path=original/'observations.jsonl'
recording=json.loads((original/'recording_report.json').read_text())
worker=json.loads((original/'observer_process_report.json').read_text())
report=dict(recording,journal_path=path.name,journal_size=path.stat().st_size,
    journal_sha256=_digest(path),records=worker['journal']['written'],errors=[],transport_errors=[],tf_api={})
values=_load_recording(original,report);loaded=time.monotonic()
result=json.loads((original/'result.json').read_text());profile=json.loads((original/'validated_profile.json').read_text())
frames=operational_frames(values['frames'])
checks=assess_frames(dict(root_source='native_ground_truth',urdf=Path(result['scene']['robot']['path']).read_text(),frames=frames),profile['limits'])
assessment=dict(scope='postmortem_all_original_operational_frames_not_new_acceptance',
    original=str(original),original_result_sha256=_digest(original/'result.json'),
    original_result_unchanged=True,original_status='FAIL',normal_shutdown_confirmed=False,
    source_journal_sha256=report['journal_sha256'],counts=recording['counts'],
    operational_frames=len(frames),load_wall_sec=loaded-started,assessment_wall_sec=time.monotonic()-loaded,
    checks=checks)
(target/'assessment.json').write_text(json.dumps(assessment,indent=2));print(json.dumps(assessment),flush=True)
