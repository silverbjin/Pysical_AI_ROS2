"""Use installed simulation packages and the existing system pytest runner."""
import sys
from pathlib import Path
def main():
    root=Path(__file__).resolve().parents[3]
    for package in ('ch13_navigation_reuse','ch13_manipulation_reuse'):
        sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/package))
    sys.path.append('/usr/lib/python3/dist-packages')
    import pytest
    paths = sys.argv[1:] or [str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse/test')]
    return pytest.main(paths+['-q','-p','no:cacheprovider'])

if __name__=='__main__':
    sys.exit(main())
