"""G09 source-only audit: paths, exact vendored bytes, lock and guide contracts.
No inference, model downloads, or training. Exit 1 on structural failure."""
import argparse,ast,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CODES={
1:"python/benchmark_torch.py",2:"python/export_yolo.py",3:"python/export_custom_model.py",4:"python/inference_onnx.py",
5:None,6:"python/ov_inference.py",7:"python/async_inference_node.py",8:"python/rgbd_sync.py",
9:"python/parameter_declaration.py",10:"python/param_callback.py",11:"python/hot_swap.py",
12:"ros2_ws/src/ch14_ai_perception/launch/robot_ai_system.launch.py",13:"python/profiler.py",
14:"docker/Dockerfile.cpu",15:"docker/run_docker.sh",16:"docker/compose.yaml",17:"python/export_rl_policy.py",
18:"python/observation_builder.py",19:"python/rl_controller.py"}
PACKAGES=("ch14_ai_common","ch14_ai_interfaces","ch14_ai_perception","ch14_performance_monitor","ch14_rl_deployment","ch14_simulation")
def blob(path):
    b=path.read_bytes();return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def audit(root):
    errors=[];codes=[];vendors=[];packages=[]
    def need(p):
        q=root/p
        if not q.is_file() or q.is_symlink():errors.append("missing/unsafe "+str(p))
        return q
    for n,p in CODES.items():
        if p:
            q=need(p);codes.append(dict(code=f"14-{n}",path=p,status="PRESENT" if q.is_file() else "MISSING"))
        else:codes.append(dict(code="14-5",path=None,status="OPTIONAL_TENSORRT_NOT_IMPLEMENTED_NOT_RUN"))
    for n in range(1,10):need(f"docs/LAB_14_{n}_GUIDE_KO.md")
    for p in ("bootstrap.sh","doctor.sh","run_lab.sh","verify_ch14.sh"):need("scripts/"+p)
    for n in PACKAGES:
        prefix=Path("ros2_ws/src")/n;q=need(prefix/"package.xml")
        try:
            node=ET.parse(q).getroot()
            if node.findtext("name")!=n:errors.append("package name "+n)
            if n=="ch14_ai_interfaces":need(prefix/"CMakeLists.txt");need(prefix/"srv/SwapModel.srv")
            else:need(prefix/"setup.py");need(prefix/"setup.cfg");need(prefix/"resource"/n)
            packages.append(n)
        except (OSError,ET.ParseError) as exc:errors.append(str(exc))
    for p in ("vendor/ch12/REUSE_MANIFEST.json","vendor/ch11_g08/REUSE_MANIFEST.json"):
        try:
            m=json.loads(need(p).read_text())
            for e in m["files"]:
                target=e["target"];q=need(target.removeprefix("Ch14/"))
                if not target.startswith("Ch14/") or ".." in Path(target).parts or blob(q)!=e["git_blob"]:errors.append("vendor drift "+target)
                else:vendors.append(target)
        except (OSError,ValueError,KeyError) as exc:errors.append(str(exc))
    for p in ("requirements/cpu.lock.txt","requirements/rl.lock.txt","requirements/openvino.lock.txt"):
        try:
            rows=[s for s in need(p).read_text().splitlines() if s.strip() and not s.startswith("#")]
            if not rows or any(not re.search(r"==\S+.*--hash=sha256:[0-9a-f]{64}",s) for s in rows):errors.append("unhashed lock "+p)
        except OSError as exc:errors.append(str(exc))
    try:
        if need("requirements/cpu.lock.txt").read_bytes()!=need("docker/requirements-cpu.txt").read_bytes():errors.append("Docker CPU lock drift")
    except OSError as exc:errors.append(str(exc))
    for q in list((root/"python").glob("*.py"))+list((root/"scripts").glob("g09*.py")):
        try:ast.parse(q.read_text(),filename=str(q))
        except (SyntaxError,OSError) as exc:errors.append(str(exc))
    return dict(status="PASS" if not errors else "FAIL",scope="G09_SOURCE_STRUCTURE_ONLY",codes=codes,packages=packages,vendor_count=len(vendors),vendor_files=vendors,guide_count=sum((root/f"docs/LAB_14_{n}_GUIDE_KO.md").is_file() for n in range(1,10)),errors=errors,full_release="HOLD")
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=ROOT);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    d=audit(a.root);a.out.write_text(json.dumps(d,indent=2)+"\n");print(json.dumps(d));raise SystemExit(bool(d["errors"]))
if __name__=="__main__":main()
