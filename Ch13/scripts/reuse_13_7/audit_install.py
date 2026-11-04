import hashlib,importlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3];output=Path(sys.argv[1]);rows=[]
subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_6/audit_install.py'),str(output.with_name('reuse_install_audit.json'))],check=True)
for source in (root/'Ch13/ros2_ws/src/ch13_mission_orchestration/ch13_mission_orchestration').glob('*.py'):
    m=importlib.import_module('ch13_mission_orchestration'+('' if source.stem=='__init__' else '.'+source.stem))
    actual=Path(m.__file__);assert '/install/' in str(actual) and source.read_bytes()==actual.read_bytes(),(source,actual)
    rows.append(dict(source=str(source),installed=str(actual),sha256=hashlib.sha256(actual.read_bytes()).hexdigest()))
import py_trees,py_trees_ros,inspect
output.write_text(json.dumps(dict(result='PASS',installed=rows,py_trees=py_trees.__file__,py_trees_ros=py_trees_ros.__file__,
    setup_signature=str(inspect.signature(py_trees_ros.trees.BehaviourTree.setup))),indent=2)+'\n')
print('BT_INSTALL_AUDIT_PASS',len(rows))
