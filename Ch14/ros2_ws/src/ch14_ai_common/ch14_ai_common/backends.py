"""Fixed FP32 YOLOv8 COCO contract. No implicit device fallback or download."""
import hashlib
import json
from pathlib import Path
import numpy as np

SHAPE_IN = (1, 3, 640, 640)
SHAPE_OUT = (1, 84, 8400)
NAMES = tuple("person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush".split(","))
CLASS_HASH = hashlib.sha256(json.dumps(NAMES, separators=(",", ":")).encode()).hexdigest()

def digest(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular file required: {path}")
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def check_tensor(x, shape):
    if not isinstance(x, np.ndarray) or x.dtype != np.float32 or x.shape != shape or not np.isfinite(x).all():
        raise ValueError(f"expected finite FP32 tensor {shape}")
    return x

def entry_for(manifest, model_id):
    if model_id not in ("yolov8n", "yolov8s"):
        raise ValueError("unsupported model id")
    rows = [m for m in manifest["models"] if m["id"] == model_id]
    if len(rows) != 1:
        raise ValueError("missing/ambiguous model manifest")
    e = rows[0]
    import re
    if not re.fullmatch(r"[0-9a-f]{64}", e.get("sha256") or ""):
        raise ValueError("missing model digest")
    return e

class TorchBackend:
    def __init__(self, path, expected_sha, device="cpu", threads=1):
        if digest(path) != expected_sha:
            raise ValueError("checkpoint SHA mismatch")
        import torch
        from ultralytics import YOLO
        if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
            raise RuntimeError("requested device unavailable")
        if threads < 1:
            raise ValueError("threads must be positive")
        torch.set_num_threads(threads)
        self.torch, self.device = torch, device
        self.net = YOLO(str(path), task="detect").model.to(device).float().eval()
        names = self.net.names
        if tuple(names[i] for i in range(80)) != NAMES or len(names) != 80:
            raise ValueError("COCO class map mismatch")
        head = self.net.model[-1]
        head.export, head.dynamic, head.format = True, False, "onnx"
        self.source_sha = expected_sha

    def prepare(self, x):
        return self.torch.from_numpy(check_tensor(x, SHAPE_IN)).to(self.device)

    def forward_device(self, x):
        with self.torch.inference_mode():
            return self.net(x)

    def sync(self):
        if self.device == "cuda":
            self.torch.cuda.synchronize()

    def forward(self, x):
        y = self.forward_device(self.prepare(x))
        return check_tensor(y.detach().cpu().numpy(), SHAPE_OUT)

class OrtBackend:
    def __init__(self, path, expected_sha, threads=1):
        if digest(path) != expected_sha:
            raise ValueError("ONNX SHA mismatch")
        if threads < 1:
            raise ValueError("threads must be positive")
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.session.disable_fallback()
        if self.session.get_providers() != ["CPUExecutionProvider"]:
            raise RuntimeError("CPU provider contract mismatch")
        ins, outs = self.session.get_inputs(), self.session.get_outputs()
        if (len(ins) != 1 or len(outs) != 1 or ins[0].name != "images" or outs[0].name != "predictions"
                or tuple(ins[0].shape) != SHAPE_IN or tuple(outs[0].shape) != SHAPE_OUT
                or ins[0].type != "tensor(float)" or outs[0].type != "tensor(float)"):
            raise ValueError("ONNX IO contract mismatch")

    def forward(self, x):
        return check_tensor(self.session.run(["predictions"], {"images": check_tensor(x, SHAPE_IN)})[0], SHAPE_OUT)

def export_yolo(backend, path):
    import onnx
    torch = backend.torch
    x = backend.prepare(np.zeros(SHAPE_IN, np.float32))
    backend.forward_device(x)
    with torch.inference_mode():
        torch.onnx.export(backend.net, x, str(path), input_names=["images"], output_names=["predictions"],
                          opset_version=13, dynamo=False, do_constant_folding=True)
    graph = onnx.load(str(path))
    onnx.checker.check_model(graph)
    if not any(o.domain in ("", "ai.onnx") and o.version == 13 for o in graph.opset_import):
        raise ValueError("ONNX opset mismatch")
    if any(n.op_type == "NonMaxSuppression" for n in graph.graph.node):
        raise ValueError("NMS must not be exported")
    return digest(path)
