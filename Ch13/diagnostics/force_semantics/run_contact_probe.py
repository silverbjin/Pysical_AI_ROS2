"""Predefined damping comparison against a joint stop, no robot or tuning."""
import hashlib, json, os, shlex, subprocess, uuid
from pathlib import Path
src=Path(__file__).resolve().parent
out=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('contact-force-'+str(uuid.uuid4()))
out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'scope':'contact_damping_semantics_not_robot_acceptance','inputs':{p.name:sha(p) for p in src.iterdir() if p.is_file()},
 'conditions_predefined':{'no_damping':0.,'native_calf_damping':10.954451150103322},'commands':[],'results':[]}
def run(cmd,label):
 manifest['commands'].append({'label':label,'argv':cmd})
 with (out/(label+'.stdout')).open('w') as a,(out/(label+'.stderr')).open('w') as b:
  r=subprocess.run(cmd,stdout=a,stderr=b,env=dict(os.environ,GZ_PARTITION=out.name),check=False)
 manifest['results'].append({'label':label,'returncode':r.returncode})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 return r.returncode
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gz-sim8'],text=True))
binary=out/'force_probe'
rc=run(['g++','-O2','-std=c++17',str(src/'force_probe.cpp'),'-o',str(binary),*flags],'build')
if rc:
 print((out/'build.stderr').read_text()[-4000:]); raise SystemExit(rc)
manifest['binary_sha256']=sha(binary)
for name,damping in manifest['conditions_predefined'].items():
 sdf=(src/'force_probe.sdf').read_text().replace('<gravity>0 0 0</gravity>', '<gravity>0 0 0</gravity><model name=\"ground\"><static>true</static><link name=\"ground\"><collision name=\"ground\"><geometry><plane><normal>0 0 1</normal><size>10 10</size></plane></geometry></collision></link></model>').replace('<model name=\"known_inertia\">', '<model name=\"known_inertia\"><pose>0 0 0.2 0 0 0</pose>').replace('<inertial>', '<collision name=\"tip\"><pose>0.1 0 -0.19 0 0 0</pose><geometry><sphere><radius>0.01</radius></sphere></geometry></collision><inertial>').replace('0.1</i', '0.01</i').replace('<damping>0</damping>',f'<damping>{damping}</damping>')
 p=out/(name+'.sdf');p.write_text(sdf)
 rc=run([str(binary),str(p),'contact_static'],name)
 print((out/(name+'.stderr')).read_text())
 import csv
 with (out/(name+'.stdout')).open() as f:rows=list(csv.DictReader(f))
 manifest.setdefault('summary',{})[name]={'first_drive':rows[10:13],'last':rows[-1]}
 # Preserve both predefined conditions even if an analytic check fails.
manifest['residual_process_lines']=[l for l in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if str(binary) in l]
manifest['output_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'path':str(out),'summary':manifest['summary'],'residual':manifest['residual_process_lines']},indent=2))
