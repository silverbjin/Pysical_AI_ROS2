"""Actual target-profile smoke, not the G01 YOLO or T03 acceptance test."""
import inspect
import json
import os
import platform
import sys
from pathlib import Path
import numpy as np
import torch
import torchvision
import cv2
import onnx
import onnxruntime as ort
import ultralytics
import rclpy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray

def main(out):
    if sys.version_info[:2] != (3, 12) or platform.machine() != "x86_64":
        raise RuntimeError("Expected Python 3.12 on x86_64")
    if np.__version__ != "1.26.4" or torch.version.cuda is not None:
        raise RuntimeError("CPU/NumPy ABI contract mismatch")
    bridge = CvBridge()
    for arr, enc in ((np.arange(18, dtype=np.uint8).reshape(2, 3, 3), "bgr8"),
                     (np.array([[0, 1000], [2000, 500]], np.uint16), "16UC1"),
                     (np.array([[0., 1.], [2., .5]], np.float32), "32FC1")):
        msg = bridge.cv2_to_imgmsg(arr, encoding=enc)
        assert isinstance(msg, Image)
        np.testing.assert_array_equal(bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough"), arr)
    rclpy.init()
    node = None
    try:
        node = rclpy.create_node("ch14_g00_probe")
        publisher = node.create_publisher(Detection2DArray, "/ch14/g00_probe", 1)
        assert publisher.topic_name == "/ch14/g00_probe"
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
    if "dynamo" not in inspect.signature(torch.onnx.export).parameters:
        raise RuntimeError("Explicit tracing exporter contract unavailable")
    torch.manual_seed(14)
    torch.set_num_threads(1)
    model = torch.nn.Sequential(torch.nn.Linear(9, 6), torch.nn.ReLU()).eval()
    x = np.random.default_rng(14).random((1, 9), dtype=np.float32)
    path = out / "g00_untrained_smoke.onnx"
    with torch.inference_mode():
        expected = model(torch.from_numpy(x)).numpy()
        torch.onnx.export(model, torch.from_numpy(x), str(path), input_names=["state"],
                          output_names=["demo"], opset_version=13, dynamo=False)
    onnx.checker.check_model(onnx.load(str(path)))
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    session.disable_fallback()
    assert session.get_providers() == ["CPUExecutionProvider"]
    actual = session.run(["demo"], {"state": x})[0]
    np.testing.assert_allclose(actual, expected, atol=1e-5, rtol=1e-4)
    result = {"scope": "G00_CPU_ABI_EXPORT_SMOKE_ONLY", "status": "PASS",
              "source_sha": os.environ.get("CH14_SOURCE_SHA"), "python": sys.version,
              "os": platform.platform(), "numpy": np.__version__, "torch": torch.__version__,
              "torchvision": torchvision.__version__, "cv2": cv2.__version__,
              "onnx": onnx.__version__, "ort": ort.__version__,
              "ultralytics": ultralytics.__version__, "ros_distro": os.environ.get("ROS_DISTRO"),
              "cv_bridge_roundtrip": ["bgr8", "16UC1", "32FC1"], "providers": session.get_providers(),
              "untrained_smoke_max_abs_error": float(np.max(np.abs(actual - expected))),
              "limitations": ["not a trained policy", "not YOLO parity", "no DDS end-to-end", "not WSL2"]}
    (out / "smoke.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main(Path(sys.argv[1]))
