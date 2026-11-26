"""Read-only source/asset preflight and result projection for original Ch13 owner.
This file imports no ROS API and publishes no control command.
"""
import argparse,hashlib,json,os,pathlib,re,subprocess,sys
from pathlib import Path
def load(path):return json.loads(Path(path).read_text())
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def need(condition,reason):
    if not condition:raise ValueError(reason)
def verify_assets(assets,rows):
    root=Path(assets).resolve(strict=True)
    need(len(rows)==94 and len({x['path'] for x in rows})==94,'ASSET_MANIFEST_COUNT')
    for row in rows:
        p=(root/row['path']).resolve()
        need(p.is_relative_to(root) and p.is_file(),'ASSET_MISSING:'+row['path'])
        need(p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'ASSET_DRIFT:'+row['path'])
    return len(rows)
def verify_source(root,contract):
    need(git(root,'rev-parse','HEAD')==contract['base_sha'],'SOURCE_SHA_DRIFT')
    need(git(root,'rev-parse','HEAD:Ch13')==contract['source_tree'],'SOURCE_TREE_DRIFT')
    need(not git(root,'status','--porcelain','--untracked-files=all','--','Ch13'),'SOURCE_DIRTY')
    for path,sha in contract['source_blobs'].items():
        need(git(root,'hash-object','--no-filters',str(root/path))==sha,'SOURCE_BLOB_DRIFT:'+path)
def verify_residual(row):
    need(row.get('result')=='PASS' and row.get('owned_stack_matches')==[] and row.get('engine_lock_free') is True,'NATIVE_RESIDUAL_OR_LOCK_BUSY')
def authorize(root,lock,contract,approval):
    verify_source(root,contract)
    need(approval is not None and approval.is_file(),'ASSET_USE_APPROVAL_MISSING')
    a=load(approval)
    need(a.get('local_use_approved') is True and a.get('redistribution') is False and a.get('upstream_commit')==lock['ch13']['upstream']['commit'] and isinstance(a.get('review_reference'),str) and bool(a['review_reference'].strip()) and not a['review_reference'].startswith('REPLACE_'),'ASSET_USE_APPROVAL_INVALID')
    assets=root.parent/'upstream-iit-locomanipulation-d010212'
    need(assets.is_dir(),'ASSETS_MISSING')
    need(git(assets,'rev-parse','HEAD')==lock['ch13']['upstream']['commit'],'ASSET_SOURCE_SHA_DRIFT')
    count=verify_assets(assets,lock['ch13']['assets'])
    shared=root.parent/'ch13_reuse_engine.lock'
    need(shared.is_file() and not shared.is_symlink(),'SHARED_LOCK_MISSING_OR_INVALID')
    return dict(result='PREFLIGHT_PASS',source='CH13_NATIVE',source_sha=contract['base_sha'],asset_count=count,assets_realpath=str(assets.resolve()),shared_lock_realpath=str(shared.resolve()),review_reference=a['review_reference'],full_mission_success=False)
def live_projection(row):
    requested=row.get('requested',[]);completed=row.get('completed',[])
    need(not {'pick','return','place'}.intersection(requested) and not {'pick','return','place'}.intersection(completed),'UNEXPECTED_MANIPULATION')
    return dict(source='CH13_NATIVE',profile='physical_basic',native_terminal=row.get('terminal'),requested=requested,completed=completed,progress=row.get('progress'),error=row.get('error'),full_mission_success=False,is_object_grasped=False)
def assess(case,after,contract,runner_exit):
    case=Path(case)
    result=load(case/'basic_result.json');bt=load(case/'bt_summary.json');nav=load(case/'navigation_summary.json')
    keys=set(contract['assessor_keys']);checks=result.get('checks',{})
    need(set(checks)==keys and all(checks[k] is True for k in keys),'NATIVE_ASSESSOR_NOT_10_OF_10')
    need(runner_exit==0 and result.get('result')=='PASS' and result.get('success') is True,'NATIVE_RUNNER_FAIL')
    need(result.get('exercise')=='basic' and result.get('scenario')=='level2_obstacles' and result.get('scope')=='basic_navigation_observation_only' and result.get('full_mission_success') is False and result.get('bag_closed') is True,'NATIVE_SCOPE_OR_RECORDING')
    port=bt.get('port',{});live_projection(port)
    need(all(x in port.get('completed',{}) for x in ('navigate','find','finish')),'NATIVE_STEPS_MISSING')
    need(bt.get('terminal')=='SUCCESS' and nav.get('result')=='PASS','NATIVE_TERMINAL')
    need(not any((case/x).exists() for x in ('trial.json','arm_probe.json','pick_mission.json')),'UNEXPECTED_MANIPULATION_ARTIFACT')
    need((case/'bag'/'metadata.yaml').is_file(),'NATIVE_BAG_MISSING')
    need((case/'source_manifest.json').is_file() and digest(case/'source_manifest.json')==result.get('source_manifest_sha256'),'NATIVE_FREEZE_DRIFT')
    verify_residual(after)
    return dict(result='PASS',profile='physical_basic',source='CH13_NATIVE',scope=result['scope'],full_mission_success=False,is_object_grasped=False,checks=checks,native_result=result)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','residual','assess','live'])
    p.add_argument('--root',type=Path);p.add_argument('--lock',type=Path);p.add_argument('--contract',type=Path)
    p.add_argument('--approval',type=Path);p.add_argument('--case',type=Path);p.add_argument('--residual',type=Path);p.add_argument('--runner-exit',type=int,default=1);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        if a.mode=='preflight':row=authorize(a.root,load(a.lock),load(a.contract),a.approval)
        elif a.mode=='residual':verify_residual(load(a.residual));row=dict(result='PASS')
        elif a.mode=='live':row=live_projection(load(a.case/'live_status.json'))
        else:row=assess(a.case,load(a.residual),load(a.contract),a.runner_exit)
        rc=0
    except Exception as e:
        row=dict(result='BLOCKED' if a.mode=='preflight' else 'FAIL',reason=str(e),source='CH13_NATIVE',full_mission_success=False);rc=2 if a.mode=='preflight' else 1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(row,indent=2,allow_nan=False)+'\n');print(json.dumps(row));return rc
if __name__=='__main__':sys.exit(main())
