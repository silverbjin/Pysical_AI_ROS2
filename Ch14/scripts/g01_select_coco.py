"""Select fixed validation images using GT only, never model predictions. No image redistribution."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor

URL="https://huggingface.co/datasets/pcuenq/coco2017-instances/resolve/0d2b1478a7c692d6227612841b28512da3def874/instances_val2017.json"
SHA="e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f"
def sha(path):
    with path.open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()
def fetch(url,path):
    subprocess.run(["curl","-fsSL","--proto","=https","--proto-redir","=https","--connect-timeout","15","--max-time","90","-o",str(path),url],check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("output",type=Path);a=p.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=False)
    ann=root/"instances_val2017.json";fetch(URL,ann)
    if sha(ann)!=SHA: raise ValueError("annotation hash mismatch")
    d=json.loads(ann.read_text());categories={c["id"]:i for i,c in enumerate(sorted(d["categories"],key=lambda c:c["id"]))}
    by={}
    for x in d["annotations"]: by.setdefault(x["image_id"],[]).append(x)
    lic={x["id"]:x for x in d["licenses"]}
    # COCO metadata: CC BY/SA or US government; exclude NC, ND and unknown.
    imgs=[x for x in d["images"] if x["license"] in (4,5,8)]
    picks=[];used=set()
    for cid in (6,17,18,24): # bus, cat, dog, zebra (COCO ids)
        cand=[]
        for im in imgs:
            if im["id"] in used: continue
            for t in by.get(im["id"],[]):
                if t["category_id"]==cid and not t["iscrowd"]:
                    x,y,w,h=t["bbox"];fraction=w*h/(im["width"]*im["height"])
                    if fraction>=.25 and x>=0 and y>=0 and x+w<=im["width"]+.01 and y+h<=im["height"]+.01:
                        cand.append((-fraction,im["id"],t["id"],im,t))
        count=0
        for _,_,_,im,t in sorted(cand,key=lambda q:q[:3]):
            if im["id"] in used:continue
            picks.append((im,[t]));used.add(im["id"]);count+=1
            if count==4:break
        if count!=4:raise ValueError("not enough positive candidates")
    negatives=[im for im in sorted(imgs,key=lambda x:x["id"]) if im["id"] not in used and not by.get(im["id"])]
    if len(negatives)<4:raise ValueError("not enough real unlabeled negatives; do not substitute")
    picks.extend((im,[]) for im in negatives[:4])
    images=root/"images";images.mkdir()
    def prepare(pair):
        im,targets=pair;name=im["file_name"];url="https://images.cocodataset.org/val2017/"+name
        if Path(name).name!=name:raise ValueError("invalid image name")
        path=images/name;fetch(url,path)
        labels=[]
        for t in targets:
            x,y,w,h=t["bbox"];labels.append({"class_id":categories[t["category_id"]],"xyxy":[x,y,x+w,y+h],"annotation_id":t["id"]})
        return dict(id=im["id"],file=name,width=im["width"],height=im["height"],sha256=sha(path),source_url=url,
                    original_flickr_url=im["flickr_url"],license_id=im["license"],license_url=lic[im["license"]]["url"],
                    license_name=lic[im["license"]]["name"],targets=labels)
    with ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(prepare,picks))
    (root/"manifest.json").write_text(json.dumps({"status":"EVALUATION_CANDIDATE_NOT_RELEASE_APPROVED","annotation_url":URL,"annotation_sha256":SHA,
      "annotation_license":"CC BY 4.0; COCO Consortium","selection":"16 largest GT targets, 4 real unlabeled negatives, no model selection",
      "images":rows},indent=2)+"\n")
if __name__=="__main__":main()
