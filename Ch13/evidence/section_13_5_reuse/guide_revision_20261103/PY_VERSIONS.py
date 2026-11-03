import sys, mujoco, torch, onnxruntime
print('Python', sys.version.split()[0])
print('MuJoCo', mujoco.__version__)
print('Torch', torch.__version__)
print('ONNX Runtime', onnxruntime.__version__)