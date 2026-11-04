"""Expose ROS apt Python dependencies after the pinned simulation venv.

Enabled only by reuse_13_7/env.sh; never installed into global Python or venv.
Appending preserves the venv's numpy/torch/mujoco priority. Children inherit the
same PYTHONPATH bootstrap instead of relying on pytest's in-process sys.path.
"""
import sys
path='/usr/lib/python3/dist-packages'
if path not in sys.path:sys.path.append(path)
