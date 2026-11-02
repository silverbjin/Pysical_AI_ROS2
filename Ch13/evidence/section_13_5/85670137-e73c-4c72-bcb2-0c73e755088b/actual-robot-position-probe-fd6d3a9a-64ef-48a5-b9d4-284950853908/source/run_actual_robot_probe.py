"""Cold stationary physical-model experiment, without ROS navigation activation."""
import hashlib,json,os,shutil,subprocess,sys,uuid,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from ament_index_python.packages import get_package_prefix
src=Path(__file__).resolve().parent
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def command(out,manifest,argv,label):
 with (out/(label+'.stdout')).open('w') as a,(out/(label+'.stderr')).open('w') as b:
  p=subprocess.run(argv,stdout=a,stderr=b,env=dict(os.environ,GZ_PARTITION=out.name),check=False)
 manifest['commands'].append({'label':label,'argv':argv,'returncode':p.returncode})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 return p.returncode

if len(sys.argv)==3 and sys.argv[1]=='--run-existing':
 out=Path(sys.argv[2]);manifest=json.loads((out/'manifest.json').read_bytes())
 assert not any(c['label']=='run' for c in manifest['commands']),'one run per UUID, never retry'
 binary=out/'build/robot_force_probe';assert sha(binary)==manifest['binary_sha256']
 for name,digest in manifest['library_sha256'].items():assert sha(Path(name))==digest
 code=command(out,manifest,[str(binary),str(out/'world.sdf'),str(out/'config.json')],'run')
 residual=[l for l in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if str(binary) in l]
 result=json.loads((out/'run.stdout').read_bytes()) if (out/'run.stdout').stat().st_size else {}
 summary={'scope':manifest['scope'],'normal_process_return':code==0,'returncode':code,
  'server_destroyed':result.get('server_destroyed',False),'ROS_shutdown':result.get('ROS_shutdown',False),
  'steps':result.get('steps'),'cases':len(result.get('cases',[])),
  'error':result.get('error'),'residual':residual,'root_source':'cold seeded native URDF diagnostic, no G1 admission',
  'controller_manager_not_exercised':True,'source_sha256':manifest['source_sha256'],
  'binary_sha256':manifest['binary_sha256'],'library_sha256':manifest['library_sha256']}
 (out/'closure.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps({'path':str(out),**summary},indent=2))
 if code:print((out/'run.stderr').read_text()[-2200:])
 raise SystemExit(code or bool(residual))

holdout= len(sys.argv)==3 and sys.argv[1]=='--prepare-balanced-holdout'
assert holdout or len(sys.argv)==2 and sys.argv[1]=='--prepare-only'
out=native/('actual-robot-position-probe-'+str(uuid.uuid4()));out.mkdir(exist_ok=False)
fixture=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_d504_infeasible.json'
f=json.loads(fixture.read_bytes());original=f['urdf'];tree=ET.fromstring(original)
trial=native/'native-contact-component-gazebo-d50469aa-b0a0-402b-b8e5-f59f21ad31a0'
frames=json.loads((trial/'all_frames.json').read_bytes())['frames']
frame=min((r for r in frames if r['stage']=='stand'),key=lambda r:abs(r['ros_ns']-15_000_000_000))
records=json.loads((trial/'native_controls.json').read_bytes())['records']
record=min(records,key=lambda r:abs(r['capture_ns']-frame['ros_ns']))
seed=frame['samples']['joints']['data']['position'];body=frame['samples']['body']['data']
control=tree.find('ros2_control');targets={};gains={};efforts={}
for row in record['joints']:
 name=row['name'];joint=control.find(f"joint[@name='{name}']")
 kp=float(joint.find("param[@name='ch13_kp']").text);gains[name]=kp;efforts[name]=row['effort_limit']
 assert abs(row['force_command'])<row['effort_limit']-.1,('saturated baseline',name)
 targets[name]=row['position_reference']['applied'] if row.get('position_reference') else row['position']+row['force_command']/kp
assert set(targets)==set(seed)
# Remove only communications/render sensors and plugins in the diagnostic copy.
# Every physical joint, inertia, collision, damper and actuator parameter stays.
def physical(tree):
 return '\n'.join(
  ET.tostring(tag,encoding='unicode') for tag in list(tree) if tag.tag in ('link','joint'))
for parent in list(tree.iter()):
 for child in list(parent):
  if child.tag in ('plugin','sensor') and parent.tag!='hardware':parent.remove(child)
# Link sensors were removed; compare the physical subtrees with sensors omitted.
check=ET.fromstring(original)
for parent in list(check.iter()):
 for child in list(parent):
  if child.tag=='sensor':parent.remove(child)
assert physical(tree)==physical(check),'physical link/joint changed while removing communications'
urdf=out/'robot_without_system_plugins.urdf';urdf.write_text(ET.tostring(tree,encoding='unicode'))
sensor_prefix=Path(get_package_prefix('integrated_robot_navigation_sensors'))
libraries={str(sensor_prefix/'lib/libnavigation_position_system.so'):sha(sensor_prefix/'lib/libnavigation_position_system.so'),
 str(sensor_prefix/'lib/libnavigation_gazebo_observation.so'):sha(sensor_prefix/'lib/libnavigation_gazebo_observation.so')}
manifest={'scope':'actual_URDF_installed_PD_stationary_position_force_model_not_G1_C1_G2',
 'uuid':out.name,'commands':[],'fixture_sha256':sha(fixture),
 'original_urdf_sha256':hashlib.sha256(original.encode()).hexdigest(),
 'physical_link_joint_sha256':hashlib.sha256(physical(check).encode()).hexdigest(),
 'source_sha256':{p.name:sha(p) for p in src.iterdir() if p.is_file()},'library_sha256':libraries,
 'seed_frame_ros_ns':frame['ros_ns'],'seed_native_capture_ns':record['capture_ns'],
 'conditions_predefined':'baseline then each12legjoint plus/minus20microrad; installed20ms reference ramp;2sec percase;last100samples',
 'model_validation_criterion_predefined':'full equilibrium derivative each input column relative vector error <=5%; raw data and any failure retained',
 'system_changes':'none; no services/clock/driver/priority changes; one finite headless process'}
code=command(out,manifest,['gz','sdf','-p',str(urdf)],'convert')
if code:print((out/'convert.stderr').read_text()[-2000:]);raise SystemExit(code)
sdf=ET.fromstring((out/'convert.stdout').read_text());model=sdf.find('model')
assert model is not None
mass=sum(float(x.text) for x in model.findall('link/inertial/mass'));assert abs(mass-15.2101)<1e-8,mass
pose=model.find('pose')
if pose is None:pose=ET.SubElement(model,'pose')
pose.text=' '.join(format(v,'.17g') for v in (*body['position'],*Rotation.from_quat(body['orientation']).as_euler('xyz')))
world=ET.fromstring('''<sdf version="1.10"><world name="stationary_robot_model"><gravity>0 0 -9.81</gravity>
<physics name="fixed2ms" type="ignored"><max_step_size>.002</max_step_size><real_time_factor>0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"><engine><filename>gz-physics-dartsim-plugin</filename></engine></plugin>
<model name="ground_plane"><static>true</static><link name="link"><collision name="collision"><geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry><surface><friction><ode><mu>1</mu><mu2>1</mu2></ode></friction></surface></collision></link></model>
</world></sdf>''')
world.find('world').append(model);ET.ElementTree(world).write(out/'world.sdf',encoding='utf-8',xml_declaration=True)
for foot in ('fr','fl','rr','rl'):
 assert len([x for x in model.findall('link/collision') if 'navcol__'+foot+'_foot__0' in x.get('name','')])==1
config={'model_name':model.get('name'),'control_urdf':original,'seed_joints':seed,'targets':targets,'gains':gains,'efforts':efforts,
 'diagnostic_seed_body':body,'original_mass_kg':mass}
if holdout:
 plan_path=Path(sys.argv[2]);plan=json.loads(plan_path.read_bytes())
 assert plan['model_parameters_fitted'] is False and plan['selection_uses_observed_derivative'] is False
 assert max(plan['exact_command_foot_L1_excursions_m'])<=40e-6
 config.update(perturbations=plan['perturbations'],input_ramp_steps=plan['input_ramp_steps'])
 shutil.copy2(plan_path,out/'holdout_plan.json')
 manifest['conditions_predefined']='baseline, plus/minus one theory-selected balanced-force combination, ramp100steps; exact footcommand excursion<=40um;3cases'
 manifest['model_validation_criterion_predefined']=plan['physical_criterion']
 manifest['book_model_validation']='book_balanced_force_v1; retain prior5percentmicroinputFAIL; independent heldout combination'
(out/'config.json').write_text(json.dumps(config,indent=2))
frozen=out/'source';frozen.mkdir()
for p in src.iterdir():
 if p.is_file():shutil.copy2(p,frozen/p.name)
include=repo/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors/include'
code=command(out,manifest,['cmake','-S',str(src),'-B',str(out/'build'),'-DCMAKE_BUILD_TYPE=Release',
 '-DCH13_SENSOR_PREFIX='+str(sensor_prefix),'-DCH13_SENSOR_INCLUDE='+str(include)],'configure')
if not code:code=command(out,manifest,['cmake','--build',str(out/'build'),'-j1'],'build')
if code:
 for label in ('configure','build'):
  p=out/(label+'.stderr')
  if p.exists():print(p.read_text()[-2400:])
 print(out);raise SystemExit(code)
manifest['binary_sha256']=sha(out/'build/robot_force_probe')
manifest['world_sha256']=sha(out/'world.sdf');manifest['config_sha256']=sha(out/'config.json')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'prepared':True,'path':str(out),'mass_kg':mass,'model_name':model.get('name'),
 'binary_sha256':manifest['binary_sha256'],'no_physics_steps_executed':True},indent=2))
