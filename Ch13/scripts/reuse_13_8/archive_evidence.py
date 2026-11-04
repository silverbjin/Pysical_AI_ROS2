"""Archive explicit 13.8 UUID cases after engine shutdown; never delete originals."""
import argparse,json
from pathlib import Path
from ch13_system_validation.evidence_archive import archive_case


def main():
    ap=argparse.ArgumentParser();ap.add_argument('cases',type=Path,nargs='+')
    ap.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[3]);args=ap.parse_args()
    for folder in args.cases:
        result=archive_case(args.repo_root,folder)
        print(json.dumps({k:result[k] for k in ('result','case','archive_bytes','archive_sha256')}))


if __name__=='__main__':main()
