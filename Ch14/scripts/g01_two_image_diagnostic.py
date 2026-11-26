"""Read-only diagnostic of two frozen inputs; never change acceptance thresholds."""
import argparse, hashlib, json, subprocess
from pathlib import Path
import numpy as np
import cv2
from dataclasses import asdict
from ch14_ai_common.backends import TorchBackend, entry_for, digest, NAMES
from ch14_ai_common.yolo import preprocess, postprocess
from ultralytics.utils import ops
try:
    from ultralytics.utils.nms import non_max_suppression
except ImportError:
    from ultralytics.utils.ops import non_max_suppression

FIXTURES=(
    (463199, 640, 480, 5, [0.,0.,640.,355.56], "eabc38a2ae22262952cc2c406be88cbc61e7d62b33d613ed040778d60064330f"),
    (392818, 500, 451, 16, [0.,10.55,500.,447.], "8918cd7c88cfe2bf32a8417abf5ad4a0402d677573c149fb29de7a6b9b6490f5"),
)
URL="https://huggingface.co/datasets/merve/coco/resolve/9e50abcdc1361852f34841af4939cbcd2d37c92f/val2017/"
CONF=.5
NMS=.45

def boxes_iou(boxes,gt):
    g=np.asarray(gt,dtype=np.float64)
    inter=np.maximum(0,np.minimum(boxes[:,2:],g[2:])-np.maximum(boxes[:,:2],g[:2])).prod(axis=1)
    area=np.maximum(0,boxes[:,2:]-boxes[:,:2]).prod(axis=1)
    union=area+(g[2]-g[0])*(g[3]-g[1])-inter
    return np.divide(inter,union,out=np.zeros_like(inter),where=union>0)

def diagnostic(raw,meta,gt,cid):
    pred=raw[0].T
    xy=pred[:,:4].astype(np.float64)
    boxes=np.column_stack((xy[:,:2]-xy[:,2:]/2,xy[:,:2]+xy[:,2:]/2))
    boxes[:,[0,2]]=np.clip((boxes[:,[0,2]]-meta.left)/meta.sx,0,meta.width)
    boxes[:,[1,3]]=np.clip((boxes[:,[1,3]]-meta.top)/meta.sy,0,meta.height)
    overlap=boxes_iou(boxes,gt)
    valid=(xy[:,2]>0)&(xy[:,3]>0)&(boxes[:,2]>boxes[:,0])&(boxes[:,3]>boxes[:,1])
    scores=pred[:,4:]
    best=scores.argmax(axis=1)
    target=scores[:,cid]
    region=valid & (overlap>=.5)
    def row(i):
        return dict(index=int(i),xyxy=boxes[i].tolist(),gt_iou=float(overlap[i]),
                    target_score=float(target[i]),top_class=NAMES[int(best[i])],
                    top_score=float(scores[i,best[i]]),
                    top3=[dict(label=NAMES[j],score=float(scores[i,j])) for j in np.argsort(-scores[i],kind="stable")[:3]])
    def top(mask,metric):
        ix=np.flatnonzero(mask)
        return [row(i) for i in ix[np.argsort(-metric[ix],kind="stable")[:5]]]
    passing=region & (target>=CONF)
    winner=passing & (best==cid)
    post=postprocess(raw,meta,CONF,NMS)
    def hit(ds):
        return any(d.class_id==cid and boxes_iou(np.asarray([d.xyxy]),gt)[0]>=.5 for d in ds)
    reason=("DETECTED" if hit(post) else
            "NO_LOCALIZATION_CANDIDATE" if not region.any() else
            "TARGET_SCORE_BELOW_THRESHOLD" if not passing.any() else
            "TARGET_NOT_ARGMAX" if not winner.any() else "NMS_OR_POSTPROCESS_LOSS")
    return dict(gt_class=NAMES[cid],gt_xyxy=gt,valid_candidates=int(valid.sum()),
                candidates_gt_iou_ge_05=int(region.sum()),target_score_ge_05=int(passing.sum()),
                target_argmax_ge_05=int(winner.sum()),top_target_global=top(valid,target),
                top_target_in_gt=top(region,target),top_object_in_gt=top(region,scores.max(axis=1)),
                custom_detections=[asdict(d) for d in post],custom_target_hit=hit(post),
                first_semantic_boundary=reason)

def upstream(raw,meta,gt,cid,torch):
    # Independent Ultralytics NMS on identical raw tensor; no second forward.
    rows=non_max_suppression(torch.from_numpy(raw.copy()),conf_thres=CONF,iou_thres=NMS,
                             multi_label=False,agnostic=False,max_det=300)[0].cpu().numpy()
    out=[]
    for r in rows:
        b=np.array(r[:4],dtype=np.float64)
        b[[0,2]]=np.clip((b[[0,2]]-meta.left)/meta.sx,0,meta.width)
        b[[1,3]]=np.clip((b[[1,3]]-meta.top)/meta.sy,0,meta.height)
        if b[2]>b[0] and b[3]>b[1]:
            out.append(dict(class_id=int(r[5]),confidence=float(r[4]),xyxy=b.tolist(),
                            gt_iou=float(boxes_iou(b[None],gt)[0])))
    return dict(detections=out,target_hit=any(r["class_id"]==cid and r["gt_iou"]>=.5 for r in out))

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/"models/model_manifest.json").read_text())
    cache=Path("/tmp/ch14-two-images");cache.mkdir(exist_ok=False)
    imgs={}
    for iid,w,h,cid,gt,sha in FIXTURES:
        fp=cache/f"{iid:012d}.jpg"
        subprocess.run(["curl","-fsSL","--proto","=https","--proto-redir","=https","--connect-timeout","15","--max-time","60","-o",str(fp),URL+fp.name],check=True)
        if digest(fp)!=sha:raise ValueError("frozen image SHA mismatch")
        img=cv2.imread(str(fp))
        if img is None or img.shape!=(h,w,3):raise ValueError("image shape mismatch")
        imgs[iid]=img
    result={"scope":"two frozen images, original PT raw and independent NMS only","conf":CONF,"nms":NMS,
            "gt_iou":.5,"prior_t04_run":45745101023,"images":[],
            "actual_weights":{},"no_threshold_or_fixture_change":True}
    for mid in ("yolov8n","yolov8s"):
        e=entry_for(manifest,mid)
        subprocess.run(["python",str(root/"scripts/fetch_models.py"),mid,"--cache","/tmp/models","--fetch","--acknowledge-agpl"],check=True)
        pt=TorchBackend(Path("/tmp/models")/(mid+".pt"),e["sha256"])
        result["actual_weights"][mid]=pt.source_sha
        for iid,w,h,cid,gt,sha in FIXTURES:
            x,meta=preprocess(imgs[iid]);raw=pt.forward(x)
            d=diagnostic(raw,meta,gt,cid)
            u=upstream(raw,meta,gt,cid,pt.torch)
            result["images"].append(dict(model=mid,id=iid,image_sha256=sha,
                input_sha256=hashlib.sha256(x.tobytes()).hexdigest(),raw_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),
                **d,upstream_nms=u))
            print(mid,iid,d["first_semantic_boundary"],"upstream_hit",u["target_hit"],flush=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    # Diagnostic execution succeeds independent of model accuracy.
    print("DIAGNOSTIC_COMPLETE_NOT_GATE_PASS")
if __name__=="__main__":main()
