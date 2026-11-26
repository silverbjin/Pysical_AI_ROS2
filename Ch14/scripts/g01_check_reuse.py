"""Verify source-identity to reuse actual G01 T01/T02 results."""
import argparse
import hashlib
import json
from pathlib import Path
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def check_fresh(previous, current, actual_hash):
    """Different bytes require fresh T02, not reuse of old T02."""
    import math
    valid=(current.get("status")=="PASS" and current.get("model")==previous["model"]
           and current.get("source_sha256")==previous["source_sha256"]
           and current.get("onnx_sha256")==actual_hash
           and current.get("class_map_sha256")==previous["class_map_sha256"]
           and all(current.get(k)==previous[k] for k in ("input_shape","output_shape","dtype","opset","nms","provider","classes"))
           and isinstance(current.get("seed_max_abs"),(int,float)) and math.isfinite(current["seed_max_abs"]))
    if not valid:raise ValueError("fresh T02 receipt/file contract invalid")
    return {"mode":"SAME_BYTES_VERIFIED" if actual_hash==previous["onnx_sha256"] else "FRESH_T02_VALIDATED_NOT_REUSED",
            "previous_onnx_sha256":previous["onnx_sha256"],"current_onnx_sha256":actual_hash}
def main():
    p=argparse.ArgumentParser();p.add_argument("receipt",type=Path);p.add_argument("output",type=Path);p.add_argument("--exports",type=Path);a=p.parse_args()
    d=json.loads(a.receipt.read_text());root=Path(__file__).resolve().parents[1]
    failures=[path for path,sha in d["prior_source_blobs"].items() if not (root/path).is_file() or blob(root/path)!=sha]
    if d["run_id"]!=45744146299 or d["internal_files_verified"]!=13 or d["t01_status"]!="SCOPED_PASS" or d["t02_status"]!="SCOPED_PASS":
        failures.append("receipt contract")
    export_match={}
    if a.exports:
        for e in d["exports"]:
            current=json.loads((a.exports/(e["model"]+"-export.json")).read_text())
            path=Path("/tmp")/e["model"]/(e["model"]+".onnx")
            try:
                with path.open("rb") as f: actual_hash=hashlib.file_digest(f,"sha256").hexdigest()
                export_match[e["model"]]=check_fresh(e,current,actual_hash)
            except (ValueError,OSError) as exc:
                failures.append(e["model"]+" "+str(exc))
    result={"status":"REUSE_VALID" if not failures else "REUSE_REJECTED","prior_run":d["run_id"],"source_sha":d["source_sha"],
            "matched_source_files":len(d["prior_source_blobs"])-sum(x in d["prior_source_blobs"] for x in failures),
            "export_validation":export_match,"errors":failures}
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
    raise SystemExit(bool(failures))
if __name__=="__main__":main()
