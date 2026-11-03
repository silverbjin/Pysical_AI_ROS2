"""Use installed simulation packages and the existing system pytest runner."""
import sys,os
from pathlib import Path
def unique_import_paths(paths):
    seen=set();result=[]
    for path in paths:
        key=os.path.abspath(path)
        if key not in seen:seen.add(key);result.append(path)
    return result


class SourceImportPaths:
    def pytest_collection_finish(self,session):
        self.before=len(sys.path);sys.path[:]=unique_import_paths(sys.path);self.after=len(sys.path)

    def pytest_runtest_setup(self,item):
        # Spawned renderers inherit repeated NTFS source roots from legacy tests.
        sys.path[:]=unique_import_paths(sys.path)


def main():
    root=Path(__file__).resolve().parents[3]
    for package in ('ch13_navigation_reuse','ch13_manipulation_reuse'):
        sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/package))
    sys.path.append('/usr/lib/python3/dist-packages')
    import pytest
    paths = sys.argv[1:] or [str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse/test')]
    import_paths=SourceImportPaths()
    result=pytest.main(paths+['-q','-p','no:cacheprovider'],plugins=[import_paths])
    print('TEST_IMPORT_PATHS',import_paths.before,'->',import_paths.after,'(first occurrence preserved)')
    return result

if __name__=='__main__':
    sys.exit(main())
