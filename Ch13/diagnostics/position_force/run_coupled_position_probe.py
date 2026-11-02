"""Predefined finite perturbations, independent response oracle and normal closure."""
import hashlib,json,os,shlex,subprocess,uuid
from pathlib import Path
import numpy as np
src=Path(__file__).resolve().parent
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
out=native/('coupled-position-probe-'+str(uuid.uuid4()));out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
damping=10.954451150103322
feet=(('fr',.25,-.15),('fl',.25,.15),('rr',-.25,-.15),('rl',-.25,.15))
links=[]
for name,x,y in feet:
 links.append(f'''<link name="{name}_foot"><pose>{x} {y} -.2 0 0 0</pose>
 <inertial><mass>.1</mass><inertia><ixx>.000016</ixx><iyy>.000016</iyy><izz>.000016</izz></inertia></inertial>
 <collision name="{name}_tip"><geometry><sphere><radius>.02</radius></sphere></geometry></collision></link>
 <joint name="{name}_slide" type="prismatic"><parent>trunk</parent><child>{name}_foot</child>
 <axis><xyz>0 0 1</xyz><limit><lower>-.1</lower><upper>.1</upper><effort>30</effort><velocity>1</velocity></limit>
 <dynamics><damping>{damping}</damping><friction>0</friction></dynamics></axis></joint>''')
sdf=out/'fixture.sdf'
sdf.write_text('''<sdf version="1.10"><world name="coupled_position_force"><gravity>0 0 -9.81</gravity>
<physics name="two_ms" type="ignored"><max_step_size>.002</max_step_size><real_time_factor>0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"><engine><filename>gz-physics-dartsim-plugin</filename></engine></plugin>
<model name="ground"><static>true</static><link name="ground"><collision name="ground"><geometry><plane><normal>0 0 1</normal><size>10 10</size></plane></geometry></collision></link></model>
<model name="four_supports"><pose>0 0 .3 0 0 0</pose><link name="trunk"><inertial><mass>1</mass><inertia><ixx>.02</ixx><iyy>.03</iyy><izz>.04</izz></inertia></inertial></link>
'''+''.join(links)+'</model></world></sdf>')
manifest={'scope':'fixed_small_position_input_four_contact_coupling_not_G1_C1_G2',
 'uuid':out.name,'sources':{p.name:sha(p) for p in (src/'coupled_position_probe.cpp',src/'run_coupled_position_probe.py',sdf)},
 'conditions_predefined':'baseline, then plus/minus100micrometers of FR,FL,RR,RL independently; ramp50steps; summarieslast200of2000steps',
 'analytical_check_predefined':'linear force derivative relative error <=2%; derivative sign and cross-leg coupling; all four supports positive, no force saturation',
 'commands':[]}
def call(cmd,label):
 with (out/(label+'.stdout')).open('w') as a,(out/(label+'.stderr')).open('w') as b:
  p=subprocess.run(cmd,stdout=a,stderr=b,env=dict(os.environ,GZ_PARTITION=out.name),check=False)
 manifest['commands'].append({'label':label,'argv':cmd,'returncode':p.returncode})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 if p.returncode:
  print((out/(label+'.stderr')).read_text()[-3000:]);print(out);raise SystemExit(p.returncode)
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gz-sim8'],text=True))
binary=out/'coupled_position_probe'
call(['g++','-O2','-std=c++17',str(src/'coupled_position_probe.cpp'),'-o',str(binary),*flags],'build')
manifest['binary_sha256']=sha(binary)
frozen=out/'source';frozen.mkdir()
for p in (src/'coupled_position_probe.cpp',src/'run_coupled_position_probe.py'):(frozen/p.name).write_bytes(p.read_bytes())
call([str(binary),str(sdf)],'run')
d=json.loads((out/'run.stdout').read_bytes());conditions=d['conditions']
b=np.array([[1.,y,-x] for _,x,y in feet]);effective=750./(1.+.002*damping/.1)
k=np.eye(4)*effective
expected=-(k-k@b@np.linalg.solve(b.T@k@b,b.T@k))
observed=np.column_stack([(np.array(conditions[1+2*i]['mean_force_z_n'])-
  np.array(conditions[2+2*i]['mean_force_z_n']))/(2*.0001) for i in range(4)])
relative=float(np.max(np.abs(observed-expected))/np.max(np.abs(expected)))
residual=[l for l in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if str(binary) in l]
summary={'scope':manifest['scope'],'server_normal_return':True,'server_destroyed':d['server_destroyed'],
 'residual_process_lines':residual,'expected_derivative_n_per_m':expected.tolist(),
 'observed_derivative_n_per_m':observed.tolist(),'relative_max_error':relative,
 'passed':bool(d['server_run_ok'] and d['server_destroyed'] and not residual and relative<=.02),
 'baseline_total_force_n':float(sum(conditions[0]['mean_force_z_n'])),
 'source_sha256':manifest['sources'],'binary_sha256':manifest['binary_sha256'],
 'caveat':'Known reduced model, not actual quadruped; validates method and coupling but not actual robot12axis response.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'path':str(out),**summary},indent=2))
raise SystemExit(0 if summary['passed'] else 1)
