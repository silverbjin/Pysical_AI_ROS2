"""Reject undefined names before spending a native engine acceptance attempt."""
import ast
from pathlib import Path
from pyflakes.checker import Checker
from pyflakes.messages import UndefinedName


def test_changed_native_dispatch_paths_have_no_unresolved_names():
    chapter=Path(__file__).resolve().parents[4]
    paths=[chapter/'scripts/run_navigation_13_5.py']
    package=Path(__file__).resolve().parents[1]/'integrated_robot_navigation'
    paths.extend(package/name for name in ('ingress_dispatch.py','crawl_controller.py','clock_execution.py'))
    failures=[]
    for path in paths:
        checker=Checker(ast.parse(path.read_text(),filename=str(path)),filename=str(path))
        failures.extend(str(path)+':'+str(message.lineno)+': '+(message.message%message.message_args)
            for message in checker.messages if isinstance(message,UndefinedName))
    assert not failures,'\n'.join(failures)
