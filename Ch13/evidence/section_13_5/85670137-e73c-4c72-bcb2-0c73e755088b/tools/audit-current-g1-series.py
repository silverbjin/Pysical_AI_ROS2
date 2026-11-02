"""Independent read-only audit of both completed fixed-source G1 series."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
series_names=('task8-fixed-g1-gazebo-series-58c7013c-863d-469a-8ff6-1863be26a9d1.json',
              'task8-fixed-g1-mujoco-series-4838bfd2-55fc-43d9-8ead-b515ece094c5.json')
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
reference=None;records=[]
for name in series_names:
    series=json.loads((base/name).read_text())
    assert series['status']=='PASS' and series['completed_consecutive_passes']==3
    assert len(series['runs'])==3 and series['stop_on_first_failure'] is True
    for index,row in enumerate(series['runs'],1):
        assert row['index']==index and row['passed'] and row['cleanup_confirmed']
        root=base/row['trial'];result=json.loads((root/'result.json').read_text())
        teardown=json.loads((root/'teardown.json').read_text())
        manifest=json.loads((root/'source_manifest.json').read_text())
        assert result['status']=='PASS' and not result['errors']
        assert all(result['checks'].get(key) is True for key in result['required_checks'])
        assert teardown['parent_reaped'] and teardown['launch_returncode']==0
        assert teardown['forced_cleanup'] is False and teardown['residual_live_pids']==[]
        assert teardown['runtime_exit'] is True and teardown['engine_exit'] is True
        if result['engine']=='gazebo':
            assert teardown['engine_returncodes']==[0] and teardown['launch_event_exit']['confirmed']
        if reference is None:reference=manifest['files']
        assert manifest['files']==reference
        for relative,expected in reference.items():assert digest(repo/relative)==expected,relative
        for artifact in result['artifacts']:
            path=root/artifact['path']
            assert path.resolve().is_relative_to(root.resolve())
            assert path.stat().st_size==artifact['size'] and digest(path)==artifact['sha256'],path
        archives=list(base.glob('task8-control-clock-'+row['trial'].removeprefix('native-g1-gazebo-')[:8]+'.json')) if result['engine']=='gazebo' else list(base.glob('task8-fixed-g1-mujoco-'+row['trial'].removeprefix('native-g1-mujoco-')[:8]+'.json'))
        assert len(archives)==1
        archive=json.loads(archives[0].read_text());zip_path=base/archive['archive']
        assert zip_path.stat().st_size==archive['size'] and digest(zip_path)==archive['sha256']
        records.append(dict(engine=result['engine'],trial=row['trial'],run_id=result['run_id'],
            checks=len(result['required_checks']),source_count=len(reference),
            source_manifest_sha256=digest(root/'source_manifest.json'),
            archive=zip_path.name,archive_size=archive['size'],archive_sha256=archive['sha256'],
            launch_returncode=0,forced_cleanup=False,residual_live_pids=[]))
report=dict(audit_uuid=str(uuid.uuid4()),status='PASS',scope='G1_only_not_G2_or_Nav2_or_section_completion',
    command=[sys.executable,*sys.argv],all_source_files_current=True,all_artifact_bytes_verified=True,
    fixed_sources_both_engines=True,records=records)
path=base/('task8-current-g1-audit-'+report['audit_uuid']+'.json')
with path.open('x') as output:json.dump(report,output,indent=2)
print(json.dumps(dict(path=str(path),status=report['status'],engines=2,consecutive_each=3,
    source_count=len(reference),runs=[(r['engine'],r['checks']) for r in records]),indent=2))
