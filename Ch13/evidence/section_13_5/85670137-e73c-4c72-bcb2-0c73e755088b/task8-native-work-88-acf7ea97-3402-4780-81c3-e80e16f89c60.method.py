"""Closed trial only: fixed observer counters, exact failed job, no new engine."""
import hashlib,json,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
names=['native-g1-gazebo-701c2860-d0a4-4377-ab9a-f0b5a9ef5f5b',
 'native-contact-component-gazebo-7e642180-032d-4077-9ee4-1a2f11fde186']
out=dict(scope='closed_owned_observer_cost_not_physics_cpu_or_causal_hardware_proof',trials=[])
for name in names:
    folder=base/name;rp=folder/'controller_report.json';report=json.loads(rp.read_text())
    current=report['first_fault'] or report['current'];cal=current['calibration']
    if cal:
        start=cal['stages'][1]['ros_ns'];end=cal['stages'][-1]['ros_ns']
    else:start=current['phase_context']['_phase_start'];end=current['ros_ns']
    raw=folder/'native_controls.json'
    if not raw.exists():raw=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'native_controls.json'
    rows=json.loads(raw.read_text())['records']
    first=max((r for r in rows if r['capture_ns']<=start),key=lambda r:r['capture_ns'])
    last=max((r for r in rows if r['capture_ns']<=end),key=lambda r:r['capture_ns'])
    stages={}
    for key in ('update','post_update','between_update_and_post'):
        a,b=first['observer_work'][key],last['observer_work'][key];count=b['calls']-a['calls']
        data={k:b[k]-a[k] for k in ('calls','wall_ns')}
        if 'cpu_ns' in a:data['cpu_ns']=b['cpu_ns']-a['cpu_ns']
        data['mean_wall_us']=data['wall_ns']/count/1000
        if 'cpu_ns' in data:data['mean_cpu_us']=data['cpu_ns']/count/1000
        stages[key]=data
    entry=dict(trial=name,start_capture_ns=first['capture_ns'],end_capture_ns=last['capture_ns'],
        received_wall_s=(last['received_ns']-first['received_ns'])/1e9,
        simulated_s=(last['capture_ns']-first['capture_ns'])/1e9,
        observer_errors=last['observer_work']['errors'],stages=stages,raw_location=str(raw),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (rp,raw)})
    if report['first_fault']:
        observation=current['load_transfer_observation'];timing=observation['attempt']['stages']
        final=timing[list(timing)[-1]]
        entry['numeric_failure']=dict(reason=current['reason'],timing=timing,
            off_cpu_or_unaccounted_wall_ns=final['wall_ns']-final['thread_cpu_ns'],
            worker=observation['worker'])
        fixture=Path('Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_7e64_xyz_budget.json')
        prior=json.loads(fixture.with_name('native_141b_xyz_budget.json').read_text())
        profile=json.loads((folder/'validated_profile.json').read_text())
        assert hashlib.sha256(prior['urdf'].encode()).hexdigest()==report['model_sha256']==profile['model_sha256']
        assert prior['limits']==profile['limits']
        value=dict(scope='exact_actual_native_qp_returned_10ms_wall_failure',urdf=prior['urdf'],limits=profile['limits'],
            args=observation['numeric_input'],provenance=dict(trial=name,model_sha256=report['model_sha256'],
                source_sha256=entry['source_sha256'],timing=timing))
        with fixture.open('x') as target:json.dump(value,target,indent=2)
        entry['fixture']=dict(path=str(fixture),bytes=fixture.stat().st_size,sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    out['trials'].append(entry)
target=base/('task8-native-work-88-'+str(uuid.uuid4())+'.json')
target.write_text(json.dumps(out,indent=2));target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=out['trials']),indent=2))
