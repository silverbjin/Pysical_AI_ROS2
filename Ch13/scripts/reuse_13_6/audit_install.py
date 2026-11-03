"""Audit this revision's installed code, data and unchanged external94 assets."""
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

root=Path(__file__).resolve().parents[3]
output=Path(sys.argv[1])
output.parent.mkdir(parents=True,exist_ok=True)
legacy_audit=output.with_name(output.stem+'_navigation.json')
subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_5/audit_r2_install.py'),str(legacy_audit)],check=True)
rows=[]
package='ch13_manipulation_reuse'
for source in (root/'Ch13/ros2_ws/src'/package/package).glob('*.py'):
    module=importlib.import_module(package+('' if source.stem=='__init__' else '.'+source.stem))
    actual=Path(module.__file__)
    assert '/install/' in str(actual) and source.read_bytes()==actual.read_bytes(),(source,actual)
    rows.append(dict(source=str(source),installed=str(actual),sha256=hashlib.sha256(actual.read_bytes()).hexdigest()))
output.write_text(json.dumps(dict(result='PASS',navigation_audit=str(legacy_audit),installed=rows),indent=2)+'\n')
print('13_6_INSTALL_AUDIT_PASS',len(rows))
