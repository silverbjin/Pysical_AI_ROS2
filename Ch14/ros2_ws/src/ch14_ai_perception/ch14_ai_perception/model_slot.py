"""Trusted local registry, CPU candidate warmup/parity and bounded worker-boundary swap.
Only the executor mutates the active generation. Loader never changes it.
"""
from dataclasses import dataclass
from pathlib import Path
import json,re,time,uuid
from queue import Queue,Empty
from threading import Thread
import numpy as np
from ch14_ai_common.backends import CLASS_HASH,SHAPE_IN,SHAPE_OUT,digest,OrtBackend,check_tensor
from ch14_ai_common.benchmark import seeded_input

PINNED={"yolov8n":"31e20dde3def09e2cf938c7be6fe23d9150bbbe503982af13345706515f2ef95",
        "yolov8s":"268e5bb54c640c96c3510224833bc2eeacab4135c6deb41502156e39986b562d"}

def sha(v):
    return isinstance(v,str) and re.fullmatch("[0-9a-f]{64}",v) is not None

@dataclass(frozen=True)
class Entry:
    model_id:str
    path:Path
    sha256:str
    reference:Path
    reference_sha256:str

@dataclass(frozen=True)
class Active:
    model_id:str
    sha256:str
    engine:object
    generation:int=0

def registry(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError("registry regular file required")
    data=json.loads(p.read_text())
    if data.get("schema")!=1:raise ValueError("registry schema")
    entries={}
    for e in data["models"]:
        i=e["model_id"]
        if i not in PINNED or i in entries or e["source_sha256"]!=PINNED[i] or e["class_map_sha256"]!=CLASS_HASH:
            raise ValueError("unapproved model id, source or class map")
        if (tuple(e["input_shape"])!=SHAPE_IN or tuple(e["output_shape"])!=SHAPE_OUT or
                e["dtype"]!="float32" or e["opset"]!=13 or e["nms"] is not False or
                not sha(e["sha256"]) or not sha(e["reference_sha256"])):
            raise ValueError("registry model contract")
        def local(name):
            rel=Path(name)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:raise ValueError("unsafe registry path")
            value=p.parent/rel
            if any(q.is_symlink() for q in [value,*value.parents] if q!=p.parent.parent):raise ValueError("symlink registry path")
            return value
        entries[i]=Entry(i,local(e["file"]),e["sha256"],local(e["reference"]),e["reference_sha256"])
    if not entries:raise ValueError("empty registry")
    return entries

def engine(path,expected,backend,threads):
    if backend=="ort":return OrtBackend(path,expected,threads)
    if backend=="openvino":
        from ch14_ai_common.ov_backend import OpenVinoBackend
        return OpenVinoBackend(path,expected,threads)
    raise ValueError("unsupported backend")

def load_candidate(e,backend,threads):
    # Local registry and exact reference bytes are prepared from the pinned publisher PT.
    if digest(e.path)!=e.sha256 or digest(e.reference)!=e.reference_sha256:raise ValueError("candidate/reference SHA mismatch")
    import onnx
    graph=onnx.load(str(e.path),load_external_data=False)
    if any(t.data_location==onnx.TensorProto.EXTERNAL for t in graph.graph.initializer):raise ValueError("external tensor data unsupported")
    onnx.checker.check_model(graph)
    if not any(o.domain in ("","ai.onnx") and o.version==13 for o in graph.opset_import) or any(n.op_type=="NonMaxSuppression" for n in graph.graph.node):
        raise ValueError("candidate ONNX contract")
    candidate=engine(e.path,e.sha256,backend,threads)
    x=seeded_input()
    ref=check_tensor(np.load(e.reference,allow_pickle=False),SHAPE_OUT)
    y=candidate.forward(x)
    np.testing.assert_allclose(y,ref,atol=1e-3,rtol=1e-3)
    # Warm up a second real inference, not a mock; validate result too.
    check_tensor(candidate.forward(x),SHAPE_OUT)
    if digest(e.path)!=e.sha256:raise ValueError("candidate changed during load")
    return candidate,{"max_abs":float(np.abs(y-ref).max()),"mean_abs":float(np.abs(y-ref).mean()),"warmup":2}

class ModelSlot:
    def __init__(self,active,entries,loader,event=lambda x:None):
        self.active=active;self.entries=entries;self.loader=loader;self.event=event
        self.pending=None;self.thread=None;self.ready=None;self.queue=Queue(maxsize=1)
        self.state="IDLE";self.last=None;self.started=None
    def log(self,state,**extra):
        row=dict(state=state,wall_ns=time.monotonic_ns(),active_id=self.active.model_id,
                 active_sha256=self.active.sha256,generation=self.active.generation,**extra)
        self.last=row;self.event(row)
        return row
    def request(self,model_id):
        if self.pending is not None:return False,"","BUSY"
        if model_id not in self.entries:return False,"","UNAPPROVED_MODEL"
        if model_id==self.active.model_id:return False,"","ALREADY_ACTIVE"
        rid=uuid.uuid4().hex;self.pending=(rid,model_id);self.state="LOADING";self.started=time.monotonic_ns()
        self.log("LOADING",request_id=rid,requested_id=model_id)
        def work():
            try:obj,metrics=self.loader(self.entries[model_id]);self.queue.put((obj,metrics,None))
            except Exception as e:self.queue.put((None,None,f"{type(e).__name__}: {e}"))
        self.thread=Thread(target=work,name="ch14-candidate-loader",daemon=True);self.thread.start()
        return True,rid,"ACCEPTED"
    def poll(self):
        if self.state!="LOADING":return
        try:obj,metrics,error=self.queue.get_nowait()
        except Empty:return
        self.thread.join()
        rid,i=self.pending
        if error:
            self.log("FAILED",request_id=rid,requested_id=i,reason=error,elapsed_ms=(time.monotonic_ns()-self.started)/1e6)
            self.pending=None;self.state="IDLE";self.thread=None
        else:
            self.ready=(obj,metrics);self.state="DRAINING"
            self.log("DRAINING",request_id=rid,requested_id=i,parity=metrics)
    def commit(self):
        if self.state!="DRAINING":raise RuntimeError("not at swap boundary")
        rid,i=self.pending;obj,metrics=self.ready
        old=self.active;self.active=Active(i,self.entries[i].sha256,obj,old.generation+1)
        self.log("SUCCEEDED",request_id=rid,requested_id=i,parity=metrics,elapsed_ms=(time.monotonic_ns()-self.started)/1e6)
        self.pending=None;self.ready=None;self.state="IDLE";self.thread=None
        # CPU backend releases runtime session by reference lifetime; no old inference remains.
        return old
    def close(self,timeout=10):
        if self.thread:
            self.thread.join(timeout)
            if self.thread.is_alive():return False
        if self.pending:
            rid,i=self.pending;self.log("CANCELLED",request_id=rid,requested_id=i,reason="shutdown")
        self.ready=None;self.pending=None;self.state="IDLE";self.thread=None
        while not self.queue.empty():self.queue.get_nowait()
        self.active=None
        return True
