"""Audit this revision's installed code, data and unchanged external94 assets."""
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from ament_index_python.packages import get_package_share_directory,get_package_prefix

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
config_share=Path(get_package_share_directory('ch13_piper_moveit_config'))/'config'
for source in (root/'Ch13/ros2_ws/src/ch13_piper_moveit_config/ch13_piper_moveit_config').glob('*.py'):
    module=importlib.import_module('ch13_piper_moveit_config'+('' if source.stem=='__init__' else '.'+source.stem))
    installed=Path(module.__file__);assert '/install/' in str(installed) and source.read_bytes()==installed.read_bytes()
    rows.append(dict(source=str(source),installed=str(installed),sha256=hashlib.sha256(installed.read_bytes()).hexdigest()))
from ch13_manipulation_reuse.model import generate_description
import mujoco
model=mujoco.MjModel.from_xml_path(str(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'))
urdf,srdf,manifest=generate_description(model)
for name,content in [('robot.urdf',urdf),('robot.srdf',srdf)]:
    installed=config_share/name;assert installed.read_text()==content+'\n',name+' generated model differs'
    rows.append(dict(generated_model=name,installed=str(installed),sha256=hashlib.sha256(installed.read_bytes()).hexdigest()))
for source in (root/'Ch13/ros2_ws/src/ch13_piper_moveit_config/config').glob('*'):
    installed=config_share/source.name;assert source.read_bytes()==installed.read_bytes()
    rows.append(dict(source=str(source),installed=str(installed),sha256=hashlib.sha256(installed.read_bytes()).hexdigest()))
planner_prefix=Path(get_package_prefix('ch13_manipulation_planner'))
planner_installed=planner_prefix/'lib/ch13_manipulation_planner/planner_runtime'
planner_build=planner_prefix.parents[1]/'build/ch13_manipulation_planner/planner_runtime'
sections={}
for section in ('.text','.rodata'):
    built=subprocess.check_output(['objcopy','-O','binary','--only-section='+section,str(planner_build),'/dev/stdout'])
    actual=subprocess.check_output(['objcopy','-O','binary','--only-section='+section,str(planner_installed),'/dev/stdout'])
    assert built==actual,'planner installed ELF differs'
    sections[section]=hashlib.sha256(actual).hexdigest()
rows.append(dict(planner_binary=str(planner_installed),sha256=hashlib.sha256(planner_installed.read_bytes()).hexdigest(),matching_sections=sections))
output.write_text(json.dumps(dict(result='PASS',navigation_audit=str(legacy_audit),installed=rows),indent=2)+'\n')
print('13_6_INSTALL_AUDIT_PASS',len(rows))
