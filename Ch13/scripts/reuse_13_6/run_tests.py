"""Use installed simulation packages and the existing system pytest runner."""
import sys
from pathlib import Path
def main():
    sys.path.append('/usr/lib/python3/dist-packages')
    import pytest
    root=Path(__file__).resolve().parents[3]
    paths = sys.argv[1:] or [str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse/test')]
    return pytest.main(paths+['-q','-p','no:cacheprovider'])

if __name__=='__main__':
    sys.exit(main())
