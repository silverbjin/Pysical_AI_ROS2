import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('verify_all',Path(__file__).parents[1]/'scripts/verify_all.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_never_converts_missing_or_failed_engine_to_pass():
    assert module.summarize({})=='FAIL'
    results={'tests':{'returncode':0},'build':{'returncode':0},'ros_tests':{'returncode':0},'mujoco':{'status':'PASS'},'mujoco_ros':{'status':'PASS'},'gazebo':{'status':'PASS','physical_grasp':{'status':'FAIL'}}}
    assert module.summarize(results)=='PARTIAL'
    results['gazebo']['status']='FAIL'
    assert module.summarize(results)=='FAIL'

def test_source_inventory_prunes_virtualenv_and_generated_output(tmp_path):
    for name in ['src/contract.py','.venv/lib/huge.py','evidence/raw.log','ros2_ws/build13_1/cache.py']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('content')
    assert set(module.source_inventory(tmp_path))=={'src/contract.py'}
