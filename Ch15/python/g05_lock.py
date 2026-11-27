"""Exact source admission; no checkout, fetch or writes."""
import json,re,sys
from pathlib import Path
import yaml

def verify(root):
    root=Path(root)
    a=yaml.safe_load((root/'dependencies/quadruped_robot.repos').read_text())
    b=yaml.safe_load((root/'dependencies/quadruped_robot.lock.repos').read_text())
    upstream=json.loads((root/'dependencies/reuse.audit.json').read_text())['ch13']['upstream']
    approval=json.loads((root/'dependencies/native_local_use_approval.json').read_text())
    expected={'repositories':{'locomanipulation-teleop-isaaclab':{'type':'git','url':upstream['url'],'version':upstream['commit']}}}
    if a!=expected or b!=expected or not re.fullmatch('[0-9a-f]{40}',upstream['commit']) or approval.get('local_use_approved') is not True or approval.get('redistribution') is not False or approval.get('upstream_commit')!=upstream['commit']:
        raise ValueError('unapproved or floating dependency')
    return {'result':'PASS','commit':upstream['commit'],'scope':'approved exact source reference; existing 94-file G04 closure reused; mock imports none'}
if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
