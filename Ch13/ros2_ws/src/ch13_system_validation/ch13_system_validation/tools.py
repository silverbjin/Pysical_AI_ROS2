"""Build and evidence isolation, without ROS imports."""
from pathlib import Path

PROTECTED=tuple('/home/jinho/'+p for p in ('ch13_reuse_r2_build','ch13_reuse_r5_build',
 'ch13_reuse_13_6_build','ch13_reuse_13_6_guide_validation_v13_20261104','ch13_reuse_13_7_build'))


def validate_build(value):
    path=Path(value).expanduser().resolve()
    for value in PROTECTED:
        protected=Path(value).resolve()
        if path==protected or path in protected.parents or protected in path.parents:
            raise ValueError('13.8 build overlaps protected install: '+str(path))
    return path


if __name__=='__main__':
    import sys
    print(validate_build(sys.argv[1]))
