"""Run one unchanged legacy workflow target with its original verdict gates."""
from pathlib import Path
import sys

engine = sys.argv[1]
if engine not in ('mujoco', 'gazebo'):
    raise ValueError(engine)
source = Path('Ch13/evidence/section_13_4/egl-424240ff/workflow/legacy.py').read_text()
source = source.replace("for engine in ('mujoco', 'gazebo'):", f'for engine in ({engine!r},):', 1)
exec(compile(source, 'legacy.py', 'exec'), {'__name__': '__legacy_target__'})
