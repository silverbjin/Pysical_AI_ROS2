"""Bounded long-term storage. This module never changes an acceptance verdict.

Raw observations are temporary inputs to the existing full-stream assessment.
Thinning happens only after the engine has been reaped and the result closed.
"""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
import zipfile

MIB = 1024**2
GIB = 1024**3
BULK_NAMES = {'observations.jsonl','observations.cdr','observations.capture',
    'observer_snapshot.pickle','replayed-snapshot.pickle','frames.json','all_frames.json',
    'native_controls.json','body_references.json','transforms.json'}
PROTECTED = {'result.json','teardown.json','source_manifest.json','install_manifest.json',
    'storage-copy-ledger.json','retention.json','retention_metrics.json'}


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(4*MIB),b''): value.update(block)
    return value.hexdigest()


def save(path, value):
    path=Path(path);temporary=path.with_name(path.name+'.retention-tmp')
    with temporary.open('w',encoding='utf-8') as output:
        json.dump(value,output,indent=2,allow_nan=False);output.write('\n')
        output.flush();os.fsync(output.fileno())
    temporary.replace(path)


def bounded(path, allowed_root):
    path=Path(path).absolute();allowed_root=Path(allowed_root).resolve(strict=True)
    if path==allowed_root or not path.is_relative_to(allowed_root):
        raise ValueError('outside evidence root')
    for parent in (path,*path.parents):
        if parent==allowed_root: break
        if parent.is_symlink(): raise ValueError('evidence symlink refused')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(allowed_root): raise ValueError('outside evidence root')
    return resolved


def bulk(name, size, minimum_bytes=4*MIB):
    path=Path(name)
    if path.name in PROTECTED or size<minimum_bytes: return False
    return (path.name in BULK_NAMES or path.suffix in ('.jsonl','.pickle','.capture','.cdr',
        '.npy','.npz','.bag','.db3','.mcap'))


def projected(row):
    value=row.get('value',row)
    if not isinstance(value,dict): return None
    keys=('ros_ns','wall_ns','stamp_ns','capture_ns','received_ns','stage','state',
          'crawl','guard','carry','startup','reason','error','position','velocity','touching')
    selected={key:value[key] for key in keys if key in value}
    samples={}
    for name,source in value.get('samples',{}).items():
        if name not in ('body','joints','contacts','imu') or not isinstance(source,dict):continue
        sample={key:source[key] for key in ('stamp_ns','received_ns','frame_id') if key in source}
        data=source.get('data',{})
        if isinstance(data,dict):
            sample['data']={key:data[key] for key in ('position','velocity','linear_velocity',
                'angular_velocity','orientation','touching','forces','names','positions','velocities') if key in data}
        samples[name]=sample
    if samples:selected['samples']=samples
    return dict(kind=row.get('kind','observation'),value=selected)


def sample_jsonl(source, target, *, max_bytes=2*MIB, interval_ns=500_000_000):
    """Preserve original times, <=2Hz per kind, bounded head and recent tail.

    Regex is only a cheap rejection prefilter. Selected rows are parsed and
    checked using the actual top-level value time before they are retained.
    """
    last={};head=[];tail=deque(maxlen=16);used=0;rows=0;selected_count=0
    with Path(source).open('rb') as stream:
        for line in stream:
            rows+=1
            kind_match=re.search(rb'"kind"\s*:\s*"([^"\\]+)"',line[:256])
            kind=kind_match.group(1).decode('ascii','replace') if kind_match else 'observation'
            stamp_match=re.search(rb'"(?:wall_ns|received_ns|capture_ns|ros_ns)"\s*:\s*(\d+)',line)
            stamp=int(stamp_match.group(1)) if stamp_match else None
            previous=last.get(kind)
            if previous is not None and (stamp is None or stamp<previous+interval_ns):continue
            try:row=json.loads(line);value=row.get('value',row)
            except (ValueError,AttributeError):continue
            if not isinstance(value,dict):continue
            actual=next((value[key] for key in ('wall_ns','received_ns','capture_ns','ros_ns')
                if type(value.get(key)) is int),None)
            if previous is not None and (actual is None or actual<previous+interval_ns):continue
            last[kind]=actual if actual is not None else 0
            item=projected(row)
            if item is None:continue
            encoded=(json.dumps(item,separators=(',',':'),allow_nan=False)+'\n').encode()
            if len(encoded)>min(64*1024,max_bytes//2):continue
            selected_count+=1
            if used+len(encoded)<=max_bytes//2:head.append(encoded);used+=len(encoded)
            else:tail.append(encoded)
    target=Path(target);target.parent.mkdir(exist_ok=True)
    with target.open('xb') as output:
        for line in head:output.write(line)
        for line in tail:
            if used+len(line)>max_bytes:break
            output.write(line);used+=len(line)
    return dict(path=str(target),bytes=used,sha256=digest(target),input_rows=rows,
        selected_before_cap=selected_count,max_rate_per_kind_hz=2,max_bytes=max_bytes,
        original_timestamps=True,scope='illustrative_sample_not_full_replay_or_acceptance')


def compact_trial(root, *, allowed_root, representative, minimum_bytes=4*MIB):
    root=bounded(root,allowed_root)
    marker=root/'retention.json'
    if marker.exists():
        old=json.loads(marker.read_text())
        if old.get('state')=='complete':
            if representative and not old.get('raw_complete'):raise ValueError('cannot promote thinned raw')
            if representative or not old.get('raw_complete'):return dict(old,already_applied=True)
            save(root/('retention.previous-'+str(uuid.uuid4())+'.json'),old)
        else:raise ValueError('incomplete retention transaction; inspect before resuming')
    result=json.loads((root/'result.json').read_text())
    closed=json.loads((root/'teardown.json').read_text())
    if closed.get('parent_reaped') is not True or closed.get('residual_live_pids')!=[]:
        raise ValueError('cleanup unconfirmed')
    paths=list(root.rglob('*'))
    if any(path.is_symlink() for path in paths):raise ValueError('evidence symlink refused')
    report=dict(schema=1,state='prepared',representative=representative,raw_complete=representative,
        result_sha256=digest(root/'result.json'),original_status=result['status'],
        created_system_ns=time.time_ns(),removed=[],removed_bytes=0,samples=[])
    metrics={key:result[key] for key in ('status','engine','gate','scenario','errors','checks',
        'required_checks','failure_phase','phase','command','execution_mode','model_sha256',
        'config_sha256','physics_sha256') if key in result}
    save(root/'retention_metrics.json',dict(metrics,raw_complete=representative))
    save(marker,report)
    if not representative:
        for path in sorted(paths):
            if not path.is_file() or not bulk(path.name,path.stat().st_size,minimum_bytes):continue
            size=path.stat().st_size;sha=digest(path)
            if path.suffix=='.jsonl':
                target=root/'retained_samples'/('__'.join(path.relative_to(root).parts))
                report['samples'].append(sample_jsonl(path,target))
            item=dict(path=str(path.relative_to(root)),size=size,sha256=sha,
                reason='closed_nonrepresentative_raw_retired',removed=False)
            report['removed'].append(item);save(marker,report)
            if path.stat().st_size!=size or digest(path)!=sha:raise ValueError('raw changed before retirement')
            path.unlink();item['removed']=True;report['removed_bytes']+=size;save(marker,report)
    if digest(root/'result.json')!=report['result_sha256']:raise ValueError('original verdict changed')
    report['state']='complete';save(marker,report)
    return report


def maintain_trials(allowed_root, *, pins=(), minimum_bytes=4*MIB):
    """Rotate completed trials only; small summaries survive every rotation.

    Called after normal cleanup, never from a sensor/control callback. A pin
    must identify still-complete raw evidence; summaries cannot be promoted.
    """
    base=Path(allowed_root).resolve(strict=True);items=[];latest={};skipped=[]
    for root in sorted(base.iterdir()):
        if not root.is_dir() or root.is_symlink() or not (root/'result.json').is_file():continue
        try:
            result=json.loads((root/'result.json').read_text());end=json.loads((root/'teardown.json').read_text())
        except (OSError,ValueError):continue
        if (end.get('parent_reaped') is not True or end.get('residual_live_pids')!=[]
                or result.get('status') not in ('PASS','FAIL')):
            skipped.append(root.name);continue
        marker=root/'retention.json'
        if marker.exists() and not json.loads(marker.read_text()).get('raw_complete'):
            if root.name in pins:raise ValueError('cannot promote thinned raw')
            continue
        key=(result.get('engine'),result.get('gate'),result.get('scenario'))
        # Different outcomes always retain separate representatives.
        key=(*key,result['status']);items.append(root)
        rank=(root/'result.json').stat().st_mtime_ns
        if key not in latest or rank>latest[key][0]:latest[key]=(rank,root.name)
    selected={row[1] for row in latest.values()}|set(pins)
    reports=[]
    for root in items:
        value=compact_trial(root,allowed_root=base,representative=root.name in selected,minimum_bytes=minimum_bytes)
        reports.append(dict(trial=root.name,raw_complete=value['raw_complete'],removed_bytes=value['removed_bytes']))
    return dict(representatives=sorted(selected),trials=reports,skipped=skipped)


def compact_archive(path, *, allowed_root, minimum_bytes=4*MIB):
    path=bounded(path,allowed_root)
    target=path.with_name(path.stem+'.metadata.zip')
    if target.exists():raise ValueError('metadata archive exists; no overwrite')
    report=dict(original=str(path),original_bytes=path.stat().st_size,original_sha256=digest(path),
        metadata=str(target),removed_members=[],raw_complete=False,state='prepared')
    with zipfile.ZipFile(path) as source,zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for item in source.infolist():
            if Path(item.filename).is_absolute() or '..' in Path(item.filename).parts:
                raise ValueError('unsafe archive member')
            if bulk(item.filename,item.file_size,minimum_bytes):
                report['removed_members'].append(dict(name=item.filename,size=item.file_size,crc32=item.CRC));continue
            with source.open(item) as stream,output.open(item.filename,'w',force_zip64=True) as dest:
                for block in iter(lambda:stream.read(4*MIB),b''):dest.write(block)
    with zipfile.ZipFile(target) as source:
        if source.testzip() is not None:raise ValueError('metadata archive CRC')
    report.update(metadata_bytes=target.stat().st_size,metadata_sha256=digest(target))
    record=path.with_name(path.stem+'.retention.json');save(record,report)
    if digest(path)!=report['original_sha256']:raise ValueError('archive changed before retirement')
    path.unlink();report['state']='complete';save(record,report)
    return report


class EvidenceBudget:
    def __init__(self,root,*,raw_bytes=2*GIB,working_bytes=8*GIB,wall_seconds=3600.,started=None):
        if min(raw_bytes,working_bytes,wall_seconds)<=0:raise ValueError('positive evidence budgets required')
        self.root=Path(root);self.raw_bytes=raw_bytes;self.working_bytes=working_bytes
        self.wall_seconds=wall_seconds;self.started=time.monotonic() if started is None else started
    def check(self,*,now=None):
        elapsed=(time.monotonic() if now is None else now)-self.started
        if elapsed>self.wall_seconds:raise RuntimeError('time_budget: evidence experiment wall limit exceeded')
        total=raw=0
        for path in self.root.rglob('*'):
            if path.is_symlink():raise RuntimeError('storage_budget: evidence symlink refused')
            if path.is_file():
                size=path.stat().st_size;total+=size
                if path.name in ('observations.cdr','observations.capture'):raw+=size
                if path.name=='observations.jsonl' and not path.with_suffix('.cdr').exists():raw+=size
        if raw>self.raw_bytes or total>self.working_bytes:
            raise RuntimeError('storage_budget: raw or working evidence byte limit exceeded')
        return dict(passed=True,raw_bytes=raw,working_bytes=total,elapsed_s=elapsed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root');parser.add_argument('--allowed-root',required=True)
    parser.add_argument('--representative',action='store_true');parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    root=bounded(args.root,args.allowed_root)
    if not args.apply:
        print(json.dumps(dict(mode='dry_run',root=str(root),representative=args.representative,
            reclaimable_bytes=0 if args.representative else sum(path.stat().st_size for path in root.rglob('*')
                if path.is_file() and not path.is_symlink() and bulk(path.name,path.stat().st_size)))));return
    value=compact_trial(root,allowed_root=args.allowed_root,representative=args.representative)
    print(json.dumps({key:value[key] for key in ('state','raw_complete','removed_bytes')}))


if __name__=='__main__':main()
