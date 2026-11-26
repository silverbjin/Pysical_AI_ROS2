"""G02 CPU benchmark and relative quality preservation; no absolute quality waiver."""
import argparse,csv,hashlib,json,os,platform,sys,time
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .backends import OrtBackend, digest, TorchBackend, entry_for
from .ov_backend import OpenVinoBackend
from .benchmark import seeded_input, summarize
from .yolo import preprocess,postprocess
from .yolo_lab import read_fixture,match,iou,save

def matched_gt(detections,labels):
    remaining={i for i,t in enumerate(labels) if not t.get("iscrowd",False)}
    hits=set()
    for d in sorted(detections,key=lambda d:-d.confidence):
        candidates=[i for i in remaining if labels[i]["class_id"]==d.class_id]
        j=max(candidates,key=lambda i:(iou(d.xyxy,labels[i]["xyxy"]),-i),default=None)
        if j is not None and iou(d.xyxy,labels[j]["xyxy"])>=.5:
            hits.add(j);remaining.remove(j)
    return hits

def required_hits(detections,targets):
    return matched_gt(detections,targets)

def parity(a,b,meta,row):
    da,db=postprocess(a,meta),postprocess(b,meta)
    pairs=match(da,db)
    hits_a=matched_gt(da,row["all_labels"]);hits_b=matched_gt(db,row["all_labels"])
    required_a=required_hits(da,row["targets"]);required_b=required_hits(db,row["targets"])
    raw=bool(np.allclose(a,b,atol=1e-3,rtol=1e-3))
    err=np.abs(a-b)
    passed=raw and not pairs["unmatched_reference"] and not pairs["unmatched_candidate"] and hits_a==hits_b and required_a==required_b
    return dict(id=row["id"],status="PASS" if passed else "FAIL",raw_allclose=raw,max_abs=float(err.max()),mean_abs=float(err.mean()),
                reference_gt_indices=sorted(hits_a),candidate_gt_indices=sorted(hits_b),new_gt_miss=sorted(hits_a-hits_b),
                new_gt_hit=sorted(hits_b-hits_a),reference_required_hits=sorted(required_a),candidate_required_hits=sorted(required_b),
                absolute_required_count=len(row["targets"]),reference=[asdict(d) for d in da],candidate=[asdict(d) for d in db],**pairs)

def timed_pair(backends,frames,mode,warmup,iterations):
    # Alternate order each sample to limit ordering bias, no async requests.
    prepared=[preprocess(img)[0] for img in frames]
    def run(name,i):
        j=i%len(frames);b=backends[name]
        if mode=="model_api":
            return b.forward(prepared[j])
        x,meta=preprocess(frames[j]);return postprocess(b.forward(x),meta)
    for i in range(warmup):
        for name in backends:run(name,i)
    vals={k:[] for k in backends};names=list(backends)
    for i in range(iterations):
        for name in (names if i%2==0 else names[::-1]):
            t=time.perf_counter_ns();run(name,i);vals[name].append((time.perf_counter_ns()-t)/1e6)
    return vals

def compare(model_path,expected_sha,fixture_manifest,images,output,threads=2,warmup=10,iterations=100,prior_sha=None,pt=None):
    if warmup<10 or iterations<100:raise ValueError("need >=10 warmup and >=100 samples")
    output.mkdir(parents=True,exist_ok=False)
    fixture_sha=digest(fixture_manifest)
    rows=list(read_fixture(fixture_manifest,images))
    engines={"ort":OrtBackend(model_path,expected_sha,threads),"openvino":OpenVinoBackend(model_path,expected_sha,threads)}
    import onnxruntime as ort
    settings={"ort":{"version":ort.__version__,"providers":engines["ort"].session.get_providers(),
                       "threads":engines["ort"].session.get_session_options().intra_op_num_threads,
                       "inter_op_threads":engines["ort"].session.get_session_options().inter_op_num_threads},
              "openvino":engines["openvino"].settings}
    results=[];fresh_pt=[]
    # If the export differs from the accepted G01 bytes, explicitly requalify only that model.
    if prior_sha is not None and expected_sha!=prior_sha and pt is None:
        raise ValueError("different ONNX needs fresh reference-model parity")
    for row,img in rows:
        x,meta=preprocess(img);a,b=(e.forward(x) for e in engines.values())
        r=parity(a,b,meta,row);r["input_sha256"]=hashlib.sha256(x.tobytes()).hexdigest();results.append(r)
        if prior_sha is not None and expected_sha!=prior_sha:fresh_pt.append(parity(pt.forward(x),a,meta,row))
    x,meta=preprocess(np.full((480,640,3),114,np.uint8))
    blank={k:len(postprocess(e.forward(x),meta)) for k,e in engines.items()}
    bad={}
    def reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError,FileNotFoundError):bad[name]=True
        else:bad[name]=False
    reject("wrong_sha",lambda:OpenVinoBackend(model_path,"0"*64,threads))
    reject("missing_file",lambda:OpenVinoBackend(output/"missing.onnx",expected_sha,threads))
    reject("non_cpu_device",lambda:OpenVinoBackend(model_path,expected_sha,threads,"GPU"))
    reject("wrong_shape",lambda:engines["openvino"].forward(np.zeros((1,3,32,32),np.float32)))
    reject("wrong_dtype",lambda:engines["openvino"].forward(np.zeros((1,3,640,640),np.float64)))
    reject("nonfinite",lambda:engines["openvino"].forward(np.full((1,3,640,640),np.nan,np.float32)))
    passed=all(r["status"]=="PASS" for r in results+fresh_pt) and not any(blank.values()) and all(bad.values())
    report=dict(status="PASS" if passed else "FAIL",scope="G02_CPU_RELATIVE_PARITY",model_sha256=expected_sha,prior_g01_sha256=prior_sha,
                g01_artifact_relation="EXACT_SHA" if expected_sha==prior_sha else "FRESH_PT_REQUALIFICATION" if prior_sha else "UNPINNED_LOCAL",
                fixture_sha256=fixture_sha,images=len(rows),settings=settings,blank=blank,negative_contracts=bad,
                results=results,fresh_pt_requalification=fresh_pt)
    save(output/"parity.json",report)
    # Preserve performance even if a parity failure occurs; final exit reflects the parity.
    timing={}
    frames=[img for _,img in rows]
    for mode in ("model_api","end_to_end"):
        vals=timed_pair(engines,frames,mode,warmup,iterations)
        timing[mode]={k:dict(**summarize(v),sequential_fps=1000/float(np.mean(v))) for k,v in vals.items()}
        with (output/(mode+".csv")).open("w") as f:
            w=csv.writer(f);w.writerow(["sample","fixture_id","ort_ms","openvino_ms"])
            w.writerows((i+1,rows[i%len(rows)][0]["id"],vals["ort"][i],vals["openvino"][i]) for i in range(iterations))
    cpu=next((l.split(":",1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name")),"unknown")
    save(output/"benchmark.json",dict(status="PASS",model_sha256=expected_sha,fixture_sha256=fixture_sha,
         settings=settings,threads=threads,warmup=warmup,iterations=iterations,cpu=cpu,affinity=sorted(os.sched_getaffinity(0)),
         platform=platform.platform(),python=sys.version,order="alternating, synchronous, batch=1",
         model_api_scope="preprocessed host FP32 -> validated host output, API/copy overhead included; no GPU transfer",
         end_to_end_scope="in-memory BGR -> letterbox -> inference -> NMS; disk/ROS excluded",timing=timing))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for mode in timing:
        vals=[timing[mode][k]["p95_ms"] for k in engines]
        fig,ax=plt.subplots();ax.bar(list(engines),vals);ax.set_ylabel("P95 latency (ms)");ax.set_title(mode)
        fig.tight_layout();fig.savefig(output/(mode+".png"));plt.close(fig)
    return report

def main():
    p=argparse.ArgumentParser()
    for n in ("onnx","fixtures","images","output"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--sha256",required=True);p.add_argument("--prior-sha");p.add_argument("--threads",type=int,default=2)
    p.add_argument("--warmup",type=int,default=10);p.add_argument("--iterations",type=int,default=100)
    p.add_argument("--pt",type=Path);p.add_argument("--pt-sha")
    a=p.parse_args()
    pt=TorchBackend(a.pt,a.pt_sha,threads=a.threads) if a.pt and a.pt_sha else None
    r=compare(a.onnx,a.sha256,a.fixtures,a.images,a.output,a.threads,a.warmup,a.iterations,a.prior_sha,pt)
    print(json.dumps({"status":r["status"],"images":r["images"],"relation":r["g01_artifact_relation"]}))
    raise SystemExit(0 if r["status"]=="PASS" else 1)
