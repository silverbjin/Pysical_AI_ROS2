import subprocess
import sys


def test_production_interpreter_imports_bt_without_pytest_path_changes():
    result=subprocess.run([sys.executable,'-c','import py_trees,py_trees_ros,pydot'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_ros_dependency_fallback_keeps_simulation_venv_numpy_first():
    result=subprocess.run([sys.executable,'-c','import numpy; print(numpy.__file__)'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    if 'ch13_reuse_iit_d010212_venv' in sys.executable:
        assert 'ch13_reuse_iit_d010212_venv' in result.stdout
