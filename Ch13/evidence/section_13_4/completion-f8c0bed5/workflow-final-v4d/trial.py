import json
import os
from pathlib import Path
import runpy
import sys

# Reuse immutable approved runner wrapper including owned-process residual gate.
sys.argv, arguments = [sys.argv[0], 'geometry'], sys.argv[1:]
source = Path('Ch13/evidence/section_13_4/egl-424240ff/workflow/native-matrix.py').read_text()
scope = {'__name__': '__completion_trial__'}
exec(compile(source.split("group = sys.argv[1]")[0], 'native-matrix.py', 'exec'), scope)
metadata = Path(os.environ['CH13_EGL_EVIDENCE']) / (arguments[0]+'-environment.json')
with metadata.open('x') as stream:
    json.dump({key: os.environ.get(key) for key in
               ('LP_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LD_PRELOAD',
                'ROS_DOMAIN_ID', 'MUJOCO_GL')}, stream, indent=2)
scope['trial'](*arguments)
