"""Developer component checks, separate from the student mission."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Ch13'))
packages=('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_mission_orchestration','ch13_system_validation')
for package in packages:sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/package))
if __name__=='__main__':
    import pytest
    sys.exit(pytest.main(['-q','-p','no:cacheprovider',
        '-o','faulthandler_timeout=60',*(str(root/'Ch13/ros2_ws/src'/p/'test') for p in packages),*sys.argv[1:]]))
