"""Fetch exact 3D evaluation asset; no Git vendoring or asset redistributions."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
def fetch(url,path,expected,size=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["curl","-fsSL","--proto","=https","--proto-redir","=https","--connect-timeout","15","--max-time","90","-o",str(path),url],check=True)
    b=path.read_bytes()
    if size is not None and len(b)!=size:raise ValueError("asset size mismatch")
    if hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()!=expected:raise ValueError("asset Git blob mismatch")
    return dict(path=str(path),git_blob=expected,sha256=hashlib.sha256(b).hexdigest(),size=len(b))
def main():
    p=argparse.ArgumentParser();p.add_argument("output",type=Path);p.add_argument("receipt",type=Path);a=p.parse_args()
    d=json.loads((Path(__file__).resolve().parents[1]/"fixtures/g03_scene.lock.json").read_text());a.output.mkdir(parents=True,exist_ok=False)
    base=f"https://raw.githubusercontent.com/{d['repo']}/{d['commit']}/"
    def one(e):
        rel=Path(e["path"])
        if rel.is_absolute() or ".." in rel.parts:raise ValueError("unsafe asset path")
        r=fetch(base+d["model"]+"/"+e["path"],a.output/d["model"]/rel,e["git_blob"],e["size"])
        r["path"]=e["path"];return r
    with ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(one,d["files"]))
    lic=fetch(base+"LICENSE",a.output/"LICENSE",d["license_git_blob"])
    a.receipt.write_text(json.dumps(dict(status="PASS",source=d,verified_files=rows,license=lic),indent=2)+"\n")
if __name__=="__main__":main()
