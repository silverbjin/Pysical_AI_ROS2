export CH13_REUSE_VENV="$HOME/physicalai_13_5/venv_reuse"
python3 -m venv "$CH13_REUSE_VENV"
"$CH13_REUSE_VENV/bin/python" -m pip install \
  --index-url https://download.pytorch.org/whl/cpu 'torch==2.9.0+cpu'
"$CH13_REUSE_VENV/bin/python" -m pip install \
  -r Ch13/evidence/section_13_5_reuse/r0-20261102/pip-freeze.txt

"$CH13_REUSE_VENV/bin/python" - <<'PY_VERSIONS'
import sys, mujoco, torch, onnxruntime
print('Python', sys.version.split()[0])
print('MuJoCo', mujoco.__version__)
print('Torch', torch.__version__)
print('ONNX Runtime', onnxruntime.__version__)
PY_VERSIONS
