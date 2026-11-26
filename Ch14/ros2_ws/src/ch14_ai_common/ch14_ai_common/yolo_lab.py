"""Codes 14-1/2/4 and actual paired YOLO validation."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
import os
import sys
import cv2
import numpy as np
from .backends import CLASS_HASH, NAMES, TorchBackend, OrtBackend, digest, entry_for, export_yolo
from .benchmark import measure, seeded_input, summarize
from .yolo import preprocess, postprocess

def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def benchmark(backend, out, warmup=10, iterations=100, threads=1):
    x = backend.prepare(seeded_input())
    vals, stats = measure(lambda: backend.forward_device(x), warmup=warmup, iterations=iterations, synchronize=backend.sync)
    np.testing.assert_allclose(list(stats.values()), list(summarize(vals).values()))
    with (out / "timings.csv").open("w") as f:
        w=csv.writer(f); w.writerow(["sample", "latency_ms"]); w.writerows(enumerate(vals, 1))
    result = dict(status="PASS", scope="model_forward_only", device=backend.device, threads=threads,
                  warmup=warmup, transfer_included=False, model_sha256=backend.source_sha,
                  torch=backend.torch.__version__, python=sys.version, platform=platform.platform(),
                  cpu_affinity=len(os.sched_getaffinity(0)), **stats)
    save(out / "benchmark.json", result)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.plot(np.arange(1, len(vals)+1), vals); plt.xlabel("Sample"); plt.ylabel("Latency (ms)")
    plt.tight_layout(); plt.savefig(out / "timings.png"); plt.close()
    return result

def iou(a,b):
    inter=max(0., min(a[2],b[2])-max(a[0],b[0]))*max(0.,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.

def match(a,b,limit=.95,score_limit=.02):
    remaining=set(range(len(b))); pairs=[]; unmatched=[]
    for x in a:
        same=[j for j in remaining if b[j].class_id==x.class_id]
        if not same:
            unmatched.append(asdict(x)); continue
        j=max(same,key=lambda k:(iou(x.xyxy,b[k].xyxy),-k))
        v=iou(x.xyxy,b[j].xyxy); d=abs(x.confidence-b[j].confidence)
        if v<limit or d>score_limit:
            unmatched.append(asdict(x)); continue
        remaining.remove(j); pairs.append({"class_id":x.class_id,"iou":v,"score_abs_diff":d})
    return {"pairs":pairs,"unmatched_reference":unmatched,"unmatched_candidate":[asdict(b[j]) for j in sorted(remaining)]}

def targets_ok(detections, targets):
    return all(any(d.class_id==t["class_id"] and iou(d.xyxy,t["xyxy"])>=.5 for d in detections) for t in targets)

def read_fixture(manifest_path, image_dir):
    rows=json.loads(manifest_path.read_text())["images"]
    if len(rows)<20 or len({r["id"] for r in rows})!=len(rows) or len({r["sha256"] for r in rows})!=len(rows):
        raise ValueError("at least 20 distinct fixed images required")
    if not any(r["targets"] for r in rows) or not any(not r["targets"] for r in rows):
        raise ValueError("positive and negative fixtures required")
    for r in rows:
        if Path(r["file"]).name!=r["file"] or not r.get("license_url") or not r.get("source_url"):
            raise ValueError("fixture provenance/path missing")
        path=image_dir/r["file"]
        if digest(path)!=r["sha256"]:
            raise ValueError("fixture SHA mismatch")
        img=cv2.imread(str(path))
        if img is None or tuple(img.shape[:2])!=(r["height"],r["width"]):
            raise ValueError("fixture decode/shape mismatch")
        yield r,img

def compare_images(pt, ort, rows, output):
    results=[]; failed=0; nonsquare=False
    for row,img in rows:
        x,meta=preprocess(img)
        a,b=pt.forward(x),ort.forward(x)
        absdiff=np.abs(a-b)
        raw=bool(np.allclose(a,b,atol=1e-3,rtol=1e-3))
        da,db=postprocess(a,meta),postprocess(b,meta)
        pairing=match(da,db)
        semantic=targets_ok(da,row["targets"]) and targets_ok(db,row["targets"])
        passed=raw and semantic and not pairing["unmatched_reference"] and not pairing["unmatched_candidate"]
        nonsquare |= img.shape[0]!=img.shape[1]
        failed+=not passed
        results.append(dict(id=row["id"],status="PASS" if passed else "FAIL",raw_allclose=raw,
                            max_abs=float(absdiff.max()),mean_abs=float(absdiff.mean()),targets_ok=semantic,
                            reference=[asdict(d) for d in da],candidate=[asdict(d) for d in db],**pairing))
    # Synthetic negative is separate from real COCO images; never substitutes for actual detections.
    x,meta=preprocess(np.full((480,640,3),114,np.uint8))
    empty=not postprocess(pt.forward(x),meta) and not postprocess(ort.forward(x),meta)
    report=dict(status="PASS" if not failed and nonsquare and empty else "FAIL", images=len(results),
                failures=failed,nonsquare=nonsquare,synthetic_empty=empty,results=results)
    save(output,report)
    return report

def infer_image(backend, image, out):
    img=cv2.imread(str(image))
    if img is None: raise ValueError("image missing or invalid")
    x,meta=preprocess(img); detections=postprocess(backend.forward(x),meta)
    out.mkdir(parents=True,exist_ok=False)
    save(out/"detections.json",[dict(**asdict(d),label=NAMES[d.class_id]) for d in detections])
    for d in detections:
        x1,y1,x2,y2=map(round,d.xyxy)
        cv2.rectangle(img,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(img,f"{NAMES[d.class_id]} {d.confidence:.2f}",(x1,max(12,y1)),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),1)
    if not cv2.imwrite(str(out/"annotated.jpg"),img): raise RuntimeError("image write failed")

def load_pt(args):
    entry=entry_for(json.loads(args.manifest.read_text()),args.model)
    return TorchBackend(args.cache/(args.model+".pt"),entry["sha256"],args.device,args.threads)

def main(command):
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    if command=="infer":
        p.add_argument("--onnx",type=Path,required=True);p.add_argument("--sha256",required=True);p.add_argument("--image",type=Path,required=True)
        p.add_argument("--threads",type=int,default=1)
        a=p.parse_args();infer_image(OrtBackend(a.onnx,a.sha256,a.threads),a.image,a.output);return
    p.add_argument("--manifest",type=Path,required=True);p.add_argument("--model",choices=["yolov8n","yolov8s"],required=True)
    p.add_argument("--cache",type=Path,required=True);p.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    p.add_argument("--threads",type=int,default=1);p.add_argument("--warmup",type=int,default=10);p.add_argument("--iterations",type=int,default=100)
    p.add_argument("--fixtures",type=Path);p.add_argument("--images",type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    pt=load_pt(a)
    if command=="benchmark":
        if a.iterations<100: raise ValueError("acceptance requires >=100 samples")
        result=benchmark(pt,a.output,a.warmup,a.iterations,a.threads)
    else:
        model=a.output/(a.model+".onnx")
        sha=export_yolo(pt,model);ort=OrtBackend(model,sha,a.threads)
        x=seeded_input();y,z=pt.forward(x),ort.forward(x)
        np.testing.assert_allclose(y,z,atol=1e-3,rtol=1e-3)
        result=dict(status="PASS",model=a.model,source_sha256=pt.source_sha,onnx_sha256=sha,model_bytes=model.stat().st_size,
                    class_map_sha256=CLASS_HASH,classes=NAMES,input_shape=[1,3,640,640],output_shape=[1,84,8400],opset=13,
                    dtype="float32",nms=False,provider="CPUExecutionProvider",seed_max_abs=float(np.abs(y-z).max()))
        save(a.output/"export.json",result)
        if a.fixtures or a.images:
            if not a.fixtures or not a.images: raise ValueError("both fixture manifest and images required")
            parity=compare_images(pt,ort,read_fixture(a.fixtures,a.images),a.output/"parity.json")
            if parity["status"]!="PASS": raise RuntimeError("fixture parity/semantic acceptance failed")
    print(json.dumps(result))
