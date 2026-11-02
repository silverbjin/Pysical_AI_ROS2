"""Exact closed G1 fault frame: same CoM/nominal IK, alternative arithmetic."""
import hashlib,json,sys,time,statistics,uuid
from pathlib import Path
import numpy as np
repo=Path.cwd();nav=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(nav))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.support import center_of_mass
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial='native-g1-gazebo-7057d83b-0627-43da-9dd6-1b091822c61a';report=base/trial/'controller_report.json'
r=json.loads(report.read_text());frame=r['first_fault'];source=nav/'test/fixtures/native_8d4f_xyz_budget.json'
case=json.loads(source.read_text());model=compile_model(case['urdf']);assert model.model_sha256==r['model_sha256']
profile=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/(trial+'-prepared')/'carry_profile.json'
limits=json.loads(profile.read_text())['limits'];assert limits==case['limits']
q=frame['samples']['joints']['data']['position'];pose=np.eye(4)
pose[:3,:3]=body_rotation(frame['samples']['body']['data'])[0];pose[:3,3]=frame['samples']['body']['data']['position']
machine=CrawlMachine(model,limits);machine.reference_body=np.array(frame['reference_body']);machine._targets={f:np.array(p) for f,p in frame['targets'].items()}
args=dict(joints=q,body=machine.reference_body,targets=machine._targets,
    envelope={f:(p[2],p[2]) for f,p in machine._targets.items()},selected=model.feet[0],future_targets=machine._targets)
out=dict(scope='closed_G1_arithmetic_comparison_not_runtime_or_motion_change',trial=trial,
    report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
    urdf_fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),samples=[])
with NativeMassEvaluator(model) as mass,NativeReferenceEnvelope(model,limits) as geometry:
    for i in range(48):
        values={};row=dict(index=i)
        for name in (('python','native') if i%2==0 else ('native','python')):
            start=time.perf_counter_ns();cpu=time.thread_time_ns()
            if name=='python':values[name]=(center_of_mass(model,q,pose),machine._solve(q,True))
            else:
                nominal=geometry.evaluate(**args)[0]
                values[name]=(mass(model,q,pose),{n:nominal[n] for n in model.joint_names})
            row[name]=dict(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu)
        row['maximum_com_difference']=float(np.max(np.abs(np.asarray(values['python'][0])-values['native'][0])))
        row['maximum_ik_difference']=max(abs(values['python'][1][n]-values['native'][1][n]) for n in model.joint_names)
        assert max(row['maximum_com_difference'],row['maximum_ik_difference'])<2e-12
        out['samples'].append(row)
    out['native_mass']=mass.provenance;out['native_geometry']=geometry.provenance
out['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
path=base/('task8-g1-native-arithmetic-'+str(uuid.uuid4())+'.json');assert not path.exists()
path.write_text(json.dumps(out,indent=2));path.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(path),median_wall_ns={k:statistics.median(r[k]['wall_ns'] for r in out['samples']) for k in ('python','native')},
    maximum_com_difference=max(r['maximum_com_difference'] for r in out['samples']),maximum_ik_difference=max(r['maximum_ik_difference'] for r in out['samples'])),indent=2))
