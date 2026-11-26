"""Optional native OpenVINO CPU backend, strict static FP32 contract."""
from .backends import digest, check_tensor, SHAPE_IN, SHAPE_OUT
import numpy as np

class OpenVinoBackend:
    def __init__(self, path, expected_sha, threads=2, device="CPU"):
        if device != "CPU":
            raise ValueError("this profile permits only explicit CPU")
        if type(threads) is not int or threads < 1:
            raise ValueError("threads must be positive")
        if digest(path) != expected_sha:
            raise ValueError("ONNX SHA mismatch")
        import openvino as ov
        self.core = ov.Core()
        if "CPU" not in self.core.available_devices:
            raise RuntimeError("OpenVINO CPU device unavailable")
        model = self.core.read_model(str(path))
        if len(model.inputs) != 1 or len(model.outputs) != 1:
            raise ValueError("expected one input/output")
        for port, name, shape in ((model.input(0),"images",SHAPE_IN),(model.output(0),"predictions",SHAPE_OUT)):
            if name not in port.get_names() or tuple(port.shape)!=shape or port.get_element_type()!=ov.Type.f32:
                raise ValueError("OpenVINO static FP32 IO contract mismatch")
        self.compiled = self.core.compile_model(model, "CPU", {
            "PERFORMANCE_HINT":"LATENCY", "INFERENCE_PRECISION_HINT":"f32",
            "INFERENCE_NUM_THREADS":threads,"NUM_STREAMS":1,"ENABLE_CPU_PINNING":False})
        devices = list(self.compiled.get_property("EXECUTION_DEVICES"))
        precision = self.compiled.get_property("INFERENCE_PRECISION_HINT")
        actual_threads = int(self.compiled.get_property("INFERENCE_NUM_THREADS"))
        streams = int(self.compiled.get_property("NUM_STREAMS"))
        if not devices or not all(d=="CPU" or d.startswith("CPU.") for d in devices):
            raise RuntimeError("non-CPU execution detected")
        if precision!=ov.Type.f32 or actual_threads!=threads or streams!=1:
            raise RuntimeError("effective precision/thread/stream mismatch")
        self.request = self.compiled.create_infer_request()
        self.settings = dict(version=ov.__version__,available_devices=list(self.core.available_devices),
            execution_devices=devices,precision=str(precision),threads=actual_threads,streams=streams,
            performance_hint=str(self.compiled.get_property("PERFORMANCE_HINT")),
            cpu_pinning=bool(self.compiled.get_property("ENABLE_CPU_PINNING")),
            full_device_name=self.core.get_property("CPU","FULL_DEVICE_NAME"))
    def forward(self, x):
        x=check_tensor(x,SHAPE_IN)
        y=self.request.infer({"images":x},share_inputs=False,share_outputs=False)[self.compiled.output(0)]
        return check_tensor(np.asarray(y),SHAPE_OUT)
