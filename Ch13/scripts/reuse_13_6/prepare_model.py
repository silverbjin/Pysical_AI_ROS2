"""Generate planning models locally; never redistribute upstream meshes/weights."""
import hashlib
import json
import sys
from pathlib import Path
import mujoco

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse'))
from ch13_manipulation_reuse.model import generate_description


def main():
    output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
    upstream=root.parent/'upstream-iit-locomanipulation-d010212'
    lock=json.loads((root/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())
    assert all(hashlib.sha256((upstream/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in lock['files'])
    model=mujoco.MjModel.from_xml_path(str(upstream/'robot_model/scene_rough.xml'))
    urdf,srdf,manifest=generate_description(model)
    for name,content in [('robot.urdf',urdf),('robot.srdf',srdf)]:
        (output/name).write_text(content+'\n');manifest[name+'_sha256']=hashlib.sha256((output/name).read_bytes()).hexdigest()
    manifest['upstream_commit']=lock['upstream']['commit']
    (output/'model_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('MODEL_GENERATED',output)


if __name__=='__main__':main()
