import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('ros_probe',Path(__file__).parents[4]/'scripts/ros_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

def result():
    return {'backend':'mujoco','probe_completed':True,'checks':dict.fromkeys(['twenty_joints','clock_advances','single_publishers','base_stable','tf_parent_unique','tf_root_observed','commands_received','tf_graph_owners','clean_shutdown'],True)}

def test_exception_cannot_pass_even_after_successful_checks():
    r=result();assert probe.probe_status(r)=='PASS'
    r['error']='finish raised';assert probe.probe_status(r)=='FAIL'

def test_missing_backend_checks_or_incomplete_probe_cannot_pass():
    r=result();r['backend']='gazebo';assert probe.probe_status(r)=='FAIL'
    r=result();r['probe_completed']=False;assert probe.probe_status(r)=='FAIL'
    r=result();r['checks'].pop('twenty_joints');assert probe.probe_status(r)=='FAIL'
