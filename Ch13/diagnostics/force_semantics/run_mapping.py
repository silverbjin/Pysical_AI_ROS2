import hashlib,json,subprocess,uuid
from pathlib import Path
src=Path(__file__).resolve().parent
out=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('dart-static-mapping-'+str(uuid.uuid4()))
out.mkdir(exist_ok=False)
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
fixture=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_d504_infeasible.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'scope':'offline_DART_mapping_not_acceptance','uuid':out.name,'inputs':{p.name:sha(p) for p in src.iterdir() if p.is_file()},'fixture_sha256':sha(fixture),'commands':[]}
commands=[('configure',['cmake','-S',str(src),'-B',str(out/'build'),'-DDART_DIR=/opt/ros/jazzy/opt/gz_dartsim_vendor/share/dart/cmake']),
 ('build',['cmake','--build',str(out/'build'),'-j1']),('evaluate',[str(out/'build/dart_static_mapping'),str(fixture)])]
for label,cmd in commands:
 with (out/(label+'.stdout')).open('w') as a,(out/(label+'.stderr')).open('w') as b:
  p=subprocess.run(cmd,stdout=a,stderr=b,check=False)
 manifest['commands'].append({'label':label,'argv':cmd,'returncode':p.returncode})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 if p.returncode:
  print((out/(label+'.stdout')).read_text()[-1800:]);print((out/(label+'.stderr')).read_text()[-1800:]);print(out);raise SystemExit(p.returncode)
print((out/'evaluate.stdout').read_text())
print(out)
