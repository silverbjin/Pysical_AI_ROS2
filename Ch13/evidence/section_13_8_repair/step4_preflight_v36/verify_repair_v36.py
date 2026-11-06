import json,hashlib
from pathlib import Path
root=Path.cwd();prep=root.parent/'section_13_8_preparation_20261104';manifest=json.loads((root/'Ch13/dependencies/section_13_8_system_v36.json').read_text());snapshot=json.loads(Path('/home/jinho/ch13_reuse_13_8_build/component_source_a53346724b3f4384842f6300c8056e5d/snapshot.json').read_text());assert manifest['source']==snapshot['files']
log=Path('/home/jinho/ch13_reuse_13_8_build/component_source_a53346724b3f4384842f6300c8056e5d/tests.log').read_text();assert '442 passed' in log and 'failed' not in log
source=root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/heading_aware_navigation.yaml';installed=Path('/home/jinho/ch13_reuse_13_8_build/install/ch13_navigation_reuse/share/ch13_navigation_reuse/config/heading_aware_navigation.yaml');assert source.read_bytes()==installed.read_bytes()
result=dict(result='PASS',source_files=len(manifest['source']),full_tests=442,test_wall_s=float(__import__('re').search(r'442 passed in ([0-9.]+)s',log).group(1)),installed_heading_config_sha256=hashlib.sha256(installed.read_bytes()).hexdigest(),meaning='all tested source bytes match v36; physical success not implied')
with (prep/'repair_v36_source_match.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))