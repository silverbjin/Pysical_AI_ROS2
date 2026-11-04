"""Check actual child interpreter imports and all four Python package bytes."""
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3];out=Path(sys.argv[1])
subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_7/audit_install.py'),str(out.with_name('bt_install_audit.json'))],check=True)
rows=[]
for package in ('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_mission_orchestration','ch13_system_validation'):
    for source in (root/'Ch13/ros2_ws/src'/package/package).glob('*.py'):
        module=importlib.import_module(package+('' if source.stem=='__init__' else '.'+source.stem))
        actual=Path(module.__file__)
        assert '/ch13_reuse_13_8_build/install/' in str(actual),(source,actual)
        assert source.read_bytes()==actual.read_bytes(),('stale installed code',source,actual)
        rows.append(dict(source=str(source.relative_to(root)),installed=str(actual),sha256=hashlib.sha256(actual.read_bytes()).hexdigest()))
import numpy,subprocess as child
version=child.check_output([sys.executable,'-c','import numpy,py_trees,py_trees_ros,rosbag2_py; print(numpy.__file__)'],text=True).strip()
assert '/ch13_reuse_iit_d010212_venv/' in version,version
out.write_text(json.dumps(dict(result='PASS',rows=rows,python=sys.executable,numpy=numpy.__file__,child_numpy=version),indent=2)+'\n')
print('VALIDATION_INSTALL_AUDIT_PASS',len(rows))
