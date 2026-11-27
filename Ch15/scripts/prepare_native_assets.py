#!/usr/bin/env python3
"""Acquire only locked upstream files. Exact Git blob and original SHA256 are separate gates.
Never overwrite an existing asset directory; never upload assets as CI artifacts.
"""
import argparse,hashlib,json,os,pathlib,sys,tempfile
from urllib.request import urlopen
from urllib.parse import quote
from pathlib import Path,PurePosixPath

TEXT={'.py','.yaml','.yml','.sh','.txt','.msg','.xml','.md','.obj','.usda','.diff'}
def digest(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def need(ok,reason):
    if not ok:raise ValueError(reason)
def select(raw,row):
    need(len(raw)==row['upstream_git_size'] and blob(raw)==row['upstream_git_blob'],'UPSTREAM_BLOB_DRIFT')
    if len(raw)==row['locked_size'] and digest(raw)==row['locked_sha256']:return raw,'EXACT_RAW'
    name=PurePosixPath(row['path'])
    need(name.suffix in TEXT or name.name=='LICENSE','NON_TEXT_DRIFT')
    raw.decode('utf-8',errors='strict')
    need(b'\0' not in raw and b'\r' not in raw,'NOT_PURE_LF_TEXT')
    data=raw.replace(b'\n',b'\r\n')
    need(len(data)==row['locked_size'] and digest(data)==row['locked_sha256'],'CRLF_CANDIDATE_MISMATCH')
    return data,'LF_TO_CRLF_EXACT_HASH'
def main():
    p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();here=Path(__file__).resolve().parents[1];lock=json.loads((here/'dependencies/reuse.audit.json').read_text())['ch13'];meta=json.loads((here/'evidence/g04/native_upstream_metadata.json').read_text());approval=json.loads((here/'dependencies/native_local_use_approval.json').read_text());target=a.target.absolute()
    rows=[];stage=None;error=None
    try:
        need(approval['local_use_approved'] is True and approval['redistribution'] is False and approval['upstream_commit']==lock['upstream']['commit'],'APPROVAL')
        need(meta['upstream_commit']==lock['upstream']['commit'],'UPSTREAM_COMMIT')
        expected={x['path']:(x['bytes'],x['sha256']) for x in lock['assets']}
        need(len(expected)==len(meta['rows'])==94 and expected=={x['path']:(x['locked_size'],x['locked_sha256']) for x in meta['rows']},'MANIFEST_MISMATCH')
        need(not target.exists() and not target.is_symlink(),'TARGET_EXISTS_READ_ONLY_NO_OVERWRITE')
        target.parent.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix='.ch15-assets-',dir=target.parent))
        for row in meta['rows']:
            rel=PurePosixPath(row['path']);need(not rel.is_absolute() and '..' not in rel.parts,'PATH_ESCAPE')
            try:
                url='https://raw.githubusercontent.com/iit-DLSLab/locomanipulation-teleop-isaaclab/'+lock['upstream']['commit']+'/'+quote(str(rel),safe='/')
                with urlopen(url,timeout=60) as response:raw=response.read(row['upstream_git_size']+1)
                data,mode=select(raw,row)
                dest=stage.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(data)
                saved=dest.read_bytes();need(len(saved)==row['locked_size'] and digest(saved)==row['locked_sha256'],'DISK_HASH_DRIFT')
                record=dict(path=str(rel),status='PASS',mode=mode,raw_bytes=len(raw),raw_sha256=digest(raw),raw_git_blob=blob(raw),verified_bytes=len(saved),verified_sha256=digest(saved))
            except Exception as exc:
                record=dict(path=str(rel),status='FAIL',error=str(exc))
            rows.append(record);print(json.dumps(record),flush=True)
        need(len(rows)==94 and all(x['status']=='PASS' for x in rows),'ASSET_VERIFICATION_FAILED')
        # Exclusive destination reservation; rename only into own empty directory.
        target.mkdir()
        stage.rename(target);stage=None
    except Exception as exc:error=str(exc)
    finally:
        result=dict(result='PASS' if error is None else 'BLOCKED',error=error,upstream_commit=lock['upstream']['commit'],count=len(rows),verified=sum(x['status']=='PASS' for x in rows),raw_exact=sum(x.get('mode')=='EXACT_RAW' for x in rows),crlf_exact=sum(x.get('mode')=='LF_TO_CRLF_EXACT_HASH' for x in rows),total_verified_bytes=sum(x.get('verified_bytes',0) for x in rows),rows=rows,redistribution=False)
        a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
        # Temporary failed candidates are not output artifacts.
        if stage is not None:
            import shutil
            shutil.rmtree(stage)
    return 0 if error is None else 2
if __name__=='__main__':sys.exit(main())
