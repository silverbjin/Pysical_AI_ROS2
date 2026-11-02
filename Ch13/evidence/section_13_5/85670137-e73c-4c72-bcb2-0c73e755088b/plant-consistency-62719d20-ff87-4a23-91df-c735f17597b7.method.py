"""Read-only current J/force/P/native command comparison; bounded export."""
import hashlib,json,uuid,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
fp=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_d504_infeasible.json'
c=json.loads(fp.read_bytes());m=compile_model(c['urdf']);a=c['args'];tree=ET.fromstring(m.urdf)
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/c['provenance']['trial']/'native_controls.json'
records=json.loads(native.read_bytes())['records'];stamp=c['provenance']['original_snapshot']['samples']['joints'][0]
near=sorted(records,key=lambda z:abs(z['capture_ns']-stamp))[:3];rows=[]
with NativeMassEvaluator(m) as core:
 jac,gravity=core.contact_terms(m,a['joints'],a['body_pose'],a['points'])
 com=np.asarray(core(m,a['joints'],np.asarray(a['body_pose'])))
 for frame in near:
  by_name={row['name']:row for row in frame['joints']}
  for foot in m.feet:
   static=np.asarray(gravity[foot])-np.asarray(jac[foot]).T@np.asarray(a['forces_world'][foot])
   for k,part in enumerate(('hip','thigh','calf')):
    n=foot[:2]+'_'+part+'_joint';native_row=by_name[n]
    gain=float(tree.find(f"ros2_control/joint[@name='{n}']/param[@name='ch13_kp']").text)
    reference=native_row.get('position_reference',{})
    rows.append({'capture_ns':frame['capture_ns'],'joint':n,'static_from_gravity_contact_nm':float(static[k]),
     'parent_requested_P_nm':gain*(a['command_joints'][n]-a['joints'][n]),
     'native_force_command_nm':native_row['force_command'],
     'projected_transmitted_nm':native_row['projected_transmitted_effort'],
     'native_damping_nm':native_row['native_damping']*native_row['velocity'],
     'native_q':native_row['position'],'parent_q':a['joints'][n],
     'position_reference':reference,
     'P_from_native_applied_reference_nm':None if 'applied' not in reference else gain*(reference['applied']-native_row['position'])})
 mass=sum(value[0] for value in m.masses.values());force=sum(np.asarray(v) for v in a['forces_world'].values())
 torque=sum(np.cross(np.asarray(a['points'][f])-com,a['forces_world'][f]) for f in m.feet)
out={'scope':'offline_model_native_consistency_not_causal_or_equilibrium_acceptance',
 'fixture_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'native_source':str(native),
 'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'parent_capture_ns':stamp,
 'total_mass_kg':mass,'com_world':com.tolist(),'contact_force_sum_n':force.tolist(),
 'contact_torque_about_com_nm':torque.tolist(),'rows':rows,
 'caveat':'Native controls are20ms samples; capture differences shown; transmitted projection is not assumed actuator effort.'}
target=b/('plant-consistency-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(target),'mass':mass,'com':com.tolist(),'force':force.tolist(),'torque':torque.tolist(),
 'fl_calf':[row for row in rows if row['joint']=='fl_calf_joint']},indent=2))
