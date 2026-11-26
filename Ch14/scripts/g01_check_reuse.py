"""Verify source-identity to reuse actual G01 T01/T02 results."""
import argparse
import hashlib
import json
from pathlib import Path
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
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
            export_match[e["model"]]=current["onnx_sha256"]==e["onnx_sha256"] and current["source_sha256"]==e["source_sha256"]
            if not export_match[e["model"]]:failures.append(e["model"]+" export bytes drift")
    result={"status":"REUSE_VALID" if not failures else "REUSE_REJECTED","prior_run":d["run_id"],"source_sha":d["source_sha"],
            "matched_source_files":len(d["prior_source_blobs"])-sum(x in d["prior_source_blobs"] for x in failures),
            "export_bytes_match":export_match,"errors":failures}
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
    raise SystemExit(bool(failures))
if __name__=="__main__":main()
