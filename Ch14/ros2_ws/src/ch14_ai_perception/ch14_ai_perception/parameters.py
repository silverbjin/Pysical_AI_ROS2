"""Read-only startup configuration and immutable per-frame threshold snapshots."""
from dataclasses import dataclass
from pathlib import Path
import math,re
from ch14_ai_common.backends import NAMES

DEFAULTS=dict(onnx="",model_path="",model_sha256="",model_id="yolov8n",model_registry="",
              backend="ort",mode="async",rgbd=False,target_frame="odom",target_class="bus",
              threads=2,delay_ms=0.,annotation=True,trace_inputs=False,
              sensor_reliability="best_effort",input_topic="/camera/color/image_raw",
              max_age_sec=.3,confidence_threshold=.5,iou_threshold=.45)
RUNTIME=frozenset(("confidence_threshold","iou_threshold"))
@dataclass(frozen=True)
class Thresholds:
    confidence:float
    iou:float

def threshold(v):
    if type(v) is not float or not math.isfinite(v) or not 0<=v<=1:
        raise ValueError("threshold must be finite double in [0,1]")
    return v

def snapshot(values):
    return Thresholds(threshold(values["confidence_threshold"]),threshold(values["iou_threshold"]))

def validate_update(items):
    seen=set()
    for k,v in items:
        if k in seen:raise ValueError("duplicate parameter")
        seen.add(k)
        if k not in RUNTIME:raise ValueError("startup-only or unknown parameter: "+k)
        threshold(v)

def validate_startup(p):
    for k,v in DEFAULTS.items():
        if type(p[k]) is not type(v):raise ValueError("invalid type: "+k)
    snapshot(p)
    if p["onnx"] and p["model_path"] and Path(p["onnx"])!=Path(p["model_path"]):raise ValueError("onnx/model_path conflict")
    path=p["model_path"] or p["onnx"]
    if not path or not Path(path).is_absolute():raise ValueError("absolute model_path required")
    if not re.fullmatch("[0-9a-f]{64}",p["model_sha256"]):raise ValueError("model SHA256 required")
    if p["model_id"] not in ("yolov8n","yolov8s"):raise ValueError("model id")
    if p["model_registry"] and not Path(p["model_registry"]).is_absolute():raise ValueError("absolute registry path required")
    if p["backend"] not in ("ort","openvino","onnx-cpu","openvino-cpu") or p["mode"] not in ("sync","async"):raise ValueError("backend/mode")
    if not 1<=p["threads"]<=32 or not math.isfinite(p["delay_ms"]) or not 0<=p["delay_ms"]<=1000:raise ValueError("threads/delay")
    if not math.isfinite(p["max_age_sec"]) or not 0<p["max_age_sec"]<=.3:raise ValueError("max age must not exceed G03 300ms")
    if p["target_class"] not in NAMES or not p["target_frame"].strip():raise ValueError("target")
    if not p["input_topic"].startswith("/") or " " in p["input_topic"]:raise ValueError("absolute input topic")
    if p["sensor_reliability"] not in ("best_effort","reliable"):raise ValueError("sensor reliability")
    if p["model_registry"] and p["mode"]!="async":raise ValueError("swap requires async mode")
    return dict(p,onnx=path,backend={"onnx-cpu":"ort","openvino-cpu":"openvino"}.get(p["backend"],p["backend"]))

def declare(node):
    from rcl_interfaces.msg import ParameterDescriptor,FloatingPointRange,SetParametersResult
    for k,v in DEFAULTS.items():
        desc=ParameterDescriptor(description="Runtime threshold" if k in RUNTIME else "Startup only",read_only=k not in RUNTIME)
        if k in RUNTIME:desc.floating_point_range=[FloatingPointRange(from_value=0.,to_value=1.,step=0.)]
        node.declare_parameter(k,v,desc)
    p=validate_startup({k:node.get_parameter(k).value for k in DEFAULTS})
    def callback(params):
        try:validate_update([(x.name,x.value) for x in params])
        except ValueError as e:return SetParametersResult(successful=False,reason=str(e))
        return SetParametersResult(successful=True)
    # No side effects in validator: get_parameters reads committed state on the executor.
    node.add_on_set_parameters_callback(callback)
    return p
