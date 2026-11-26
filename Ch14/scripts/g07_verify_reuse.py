"""Verify exact G07 generated model and metadata before loading. No retraining."""
import argparse,hashlib,json
from pathlib import Path
EXPECTED={
  "smoke_bundle/final_model.zip": "45b2450e95d68d258c5d437b3a59d04c37a7d84f5b9ac9cb119c6c2d2002f2ce",
  "smoke_bundle/manifest.json": "f019c67de3aad30e4b020538546fc10154aabf5fb3d5bbb0d453a7512cbbe7a9",
  "smoke_bundle/result.json": "91b1fddb8adbfe712dadc977cf3decf668b01defb61a8d6529d024054f1ff1e1",
  "smoke-receipt.json": "0b280bd2506dc272e3bed4519401e55d6bf4970cde9c20f012c6eb1e3bdcdb70",
  "export/quadruped_policy.onnx": "c6bc846346ea156f39b31a84da3e2051e17d377b39b825eb08ba3ef77f51e546",
  "export/policy_contract.json": "1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168",
  "export/parity_samples.npz": "1560cda534f40e61b21d3b75b36a0a2c20fdaf9fffc027bea3698a87f876ff9b",
  "export/sensor_replay.json": "a989a6e2e3b0c7f0a22073a5d13c8f89e9efe8c268a466677fcce71397e5968a",
  "shadow-dds.json": "e7cfeab6b5d4bd17b0d109d31d4a6d351e9aa5bd4375ff6b27d0608297ecb980",
  "rl-install-report.json": "f0c9c3e46953aa60266f191aedd3ea55c71f2b08a10f95e2ee266a0b5b80d6dd",
  "sha256sums.txt": "4693e03782b9bc5cbed3e4f94cc266114576e3a6b8ef2584683dadcad434fb0d"
}
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);a=p.parse_args()
    for name,expected in EXPECTED.items():
        f=a.root/name
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:raise ValueError("G07 reuse integrity: "+name)
    print(json.dumps(dict(status="G07_REUSE_VERIFIED",files=len(EXPECTED),scope="SMOKE_ONLY",source_run=45763347165)))
if __name__=="__main__":main()
