import json,hashlib
from pathlib import Path
root=Path.cwd();prep=root.parent/'section_13_8_preparation_20261104';manifest=json.loads((root/'Ch13/dependencies/section_13_8_system_v35.json').read_text());snapshot=json.loads(Path('/home/jinho/ch13_reuse_13_8_build/component_source_6c19526f2e084f40b1002a27785fbc5e/snapshot.json').read_text());assert manifest['source']==snapshot['files']
log=Path('/home/jinho/ch13_reuse_13_8_build/component_source_6c19526f2e084f40b1002a27785fbc5e/tests.log').read_text();assert '437 passed' in log and 'failed' not in log
source=root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/heading_aware_navigation.yaml';installed=Path('/home/jinho/ch13_reuse_13_8_build/install/ch13_navigation_reuse/share/ch13_navigation_reuse/config/heading_aware_navigation.yaml');assert source.read_bytes()==installed.read_bytes()
result=dict(result='PASS',source_files=len(manifest['source']),full_tests=437,test_wall_s=float(__import__('re').search(r'437 passed in ([0-9.]+)s',log).group(1)),installed_heading_config_sha256=hashlib.sha256(installed.read_bytes()).hexdigest(),meaning='all tested source bytes match v35; physical success not implied')
with (prep/'repair_v35_source_match.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))