"""Code 14-3: deterministic untrained MLP, never a motor policy."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def demo_model():
    import torch
    from torch import nn
    # Do not change the caller's global RNG state.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(14)
        model = nn.Sequential(nn.Linear(9, 64), nn.ReLU(), nn.Linear(64, 64),
                              nn.ReLU(), nn.Linear(64, 6))
    return model.float().eval()


def demo_inputs():
    random = np.random.default_rng(14).standard_normal((96, 9)).astype(np.float32)
    return np.concatenate((np.zeros((1, 9), np.float32), np.ones((1, 9), np.float32),
                           -np.ones((1, 9), np.float32), np.full((1, 9), 10, np.float32), random))


def export_custom(output):
    import torch
    import onnx
    import onnxruntime as ort
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    model = demo_model()
    inputs = demo_inputs()
    path = root / 'robot_arm_controller.onnx'
    try:
        with torch.inference_mode():
            torch.onnx.export(model, torch.zeros(1, 9), str(path),
                              input_names=['input_state'], output_names=['joint_vel_cmd'],
                              opset_version=13, dynamo=False)
            expected = np.concatenate([model(torch.from_numpy(x[None])).numpy() for x in inputs])
        graph = onnx.load(str(path))
        onnx.checker.check_model(graph)
        if not any(x.domain in ('', 'ai.onnx') and x.version == 13 for x in graph.opset_import):
            raise ValueError('unexpected ONNX opset')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
        session.disable_fallback()
        if session.get_providers() != ['CPUExecutionProvider']:
            raise RuntimeError('CPU provider not active')
        ins, outs = session.get_inputs(), session.get_outputs()
        if (len(ins) != 1 or len(outs) != 1 or ins[0].name != 'input_state' or
                outs[0].name != 'joint_vel_cmd' or ins[0].shape != [1, 9] or
                outs[0].shape != [1, 6] or ins[0].type != 'tensor(float)' or outs[0].type != 'tensor(float)'):
            raise ValueError('MLP IO contract mismatch')
        actual = np.concatenate([session.run(['joint_vel_cmd'], {'input_state': x[None]})[0] for x in inputs])
        if actual.shape != (100, 6) or not np.isfinite(actual).all() or not np.isfinite(expected).all():
            raise ValueError('invalid output')
        np.testing.assert_allclose(actual, expected, atol=1e-5, rtol=1e-4)
        np.savez(root / 'reference_outputs.npz', inputs=inputs, pytorch=expected, onnx=actual)
        report = dict(status='PASS', scope='T03_UNTRAINED_DEMO', samples=len(inputs),
                      model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      max_abs_error=float(np.max(np.abs(actual - expected))),
                      atol=1e-5, rtol=1e-4, providers=session.get_providers(),
                      torch=torch.__version__, onnx=onnx.__version__, ort=ort.__version__, numpy=np.__version__,
                      motor_command=False)
    except Exception as e:
        (root / 'result.json').write_text(json.dumps(dict(status='FAIL', scope='T03_UNTRAINED_DEMO', reason=repr(e))) + '\n')
        raise
    (root / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True, help='new evidence directory')
    a = p.parse_args()
    print(json.dumps(export_custom(a.output), indent=2))
