import argparse,json
from pathlib import Path
from ch13_mission_orchestration.mock import run_mock
ap=argparse.ArgumentParser();ap.add_argument('case',choices=['normal','low_battery','fallen','not_found']);ap.add_argument('output',type=Path)
args=ap.parse_args()
if args.output.exists():raise ValueError('new output required')
data=run_mock(args.case);args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:data[k] for k in ('profile','case','terminal','requested')}))
