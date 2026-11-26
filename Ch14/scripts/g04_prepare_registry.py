"""Generate local-only approved registry and PT reference tensors; no binary publication."""
import argparse,json
from pathlib import Path
import numpy as np
from ch14_ai_common.backends import TorchBackend,OrtBackend,CLASS_HASH,SHAPE_IN,SHAPE_OUT,digest,export_yolo,entry_for
from ch14_ai_common.benchmark import seeded_input
def main():
    p=argparse.ArgumentParser();p.add_argument("--cache",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(a.manifest.read_text());rows=[];receipts=[]
    for i in ("yolov8n","yolov8s"):
        e=entry_for(manifest,i);pt=TorchBackend(a.cache/(i+".pt"),e["sha256"],"cpu",1)
        path=a.output/(i+".onnx");h=export_yolo(pt,path)
        x=seeded_input();ref=pt.forward(x);actual=OrtBackend(path,h,1).forward(x)
        np.testing.assert_allclose(actual,ref,atol=1e-3,rtol=1e-3)
        refpath=a.output/(i+".npy");np.save(refpath,ref,allow_pickle=False)
        row=dict(model_id=i,source_sha256=e["sha256"],file=path.name,sha256=h,reference=refpath.name,
                 reference_sha256=digest(refpath),class_map_sha256=CLASS_HASH,input_shape=list(SHAPE_IN),output_shape=list(SHAPE_OUT),dtype="float32",opset=13,nms=False)
        rows.append(row);receipts.append(dict(**row,seed_max_abs=float(np.abs(actual-ref).max()),status="PASS"))
        del pt
    (a.output/"registry.json").write_text(json.dumps(dict(schema=1,models=rows),indent=2)+"\n")
    a.receipt.write_text(json.dumps(dict(status="PASS",scope="local candidate provenance and seed parity; not full semantic rerun",models=receipts),indent=2)+"\n")
if __name__=="__main__":main()
