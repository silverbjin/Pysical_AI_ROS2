import hashlib,json,sys,uuid
from pathlib import Path
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2');n=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(n))
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.contact_equilibrium import static_support
f=json.loads((n/'test/fixtures/native_d504_infeasible.json').read_bytes());a=f['args'];model=compile_model(f['urdf'])
with NativeMassEvaluator(model) as mass:
 m=CrawlMachine(model,f['limits'],mass_evaluator=mass,load_transfer_policy='coupled_contact',async_load_transfer=True,load_result_timing='same_cycle',load_receipt_mode='event_receiver');m.state='CRAWL';m._index=m.ORDER.index(a['foot']);actuator=m._actuation_evaluator
 try:
  center=mass(model,a['joints'],a['body_pose']);active=tuple(foot for foot in model.feet if foot!=a['foot'])
  old=static_support(model,a['joints'],a['body_pose'],a['points'],active,com=center,terms_evaluator=mass.contact_terms)
  new=m._support_actuation(a['joints'],a['body_pose'],center,a['points'])
  assert new['feasible'] and len(new['actuator_command_efforts'])==20
  output=dict(scope='offline actual-owner support map at failed267; no physical engine or C1 acceptance',legacy_physical_utilization=old['torque_utilization'],discrete_result=new,
    original_actuator_caps={name:model.limits[name][3] for name in new['actuator_command_efforts']},library_provenance=actuator.provenance,
    fixture_sha256=hashlib.sha256((n/'test/fixtures/native_d504_infeasible.json').read_bytes()).hexdigest(),method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 finally:m.close_load_transfer()
 output['owned_static_plan_closed']=not actuator._finalize.alive;assert output['owned_static_plan_closed']
b=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';p=b/('discrete-support-owner-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(output,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),'old_usage':old['torque_utilization'],'new_usage':new['torque_utilization'],'feasible':new['feasible'],'owned_plan_closed':output['owned_static_plan_closed']},indent=2))
