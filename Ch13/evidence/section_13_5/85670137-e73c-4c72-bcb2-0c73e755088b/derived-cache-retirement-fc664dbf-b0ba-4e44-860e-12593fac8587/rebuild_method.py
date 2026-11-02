"""Postmortem only: time original complete JSON -> pickle -> hash path, no ROS."""
import gc,hashlib,json,pickle,time,uuid,resource
from pathlib import Path
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
original=root/'native-g2-mujoco-e5f0aea4-bbea-427d-8d25-f020bfbe78fd'
target=root/('observer-export-replay-'+str(uuid.uuid4()));target.mkdir()
started=time.monotonic();report=dict(original=str(original),phases={},physical_acceptance=False)
def mark(name):
    report['phases'][name]=time.monotonic()-started
    report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    (target/'timings.json').write_text(json.dumps(report,indent=2));print(name,report['phases'][name],flush=True)
print('REPLAY',target,flush=True)
streams={key:[] for key in ('frame','native_controls','body_reference','tf_transform')}
with (original/'observations.jsonl').open(encoding='utf-8') as source:
    for line in source:
        row=json.loads(line)
        if row['kind'] in streams:streams[row['kind']].append(row['value'])
expected=json.loads((original/'recording_report.json').read_text())['counts']
assert all(len(rows)==expected.get(key,0) for key,rows in streams.items())
report['counts']={key:len(rows) for key,rows in streams.items()};mark('whole_json_restored')
snapshot=dict(frames=streams['frame'],native_controls=streams['native_controls'],
    body_references=streams['body_reference'],transforms=streams['tf_transform'],errors=[],transport_errors=[],tf_api={})
path=target/'replayed-snapshot.pickle'
with path.open('xb') as output:pickle.dump(snapshot,output,protocol=5)
mark('pickle_written')
sha=hashlib.sha256()
with path.open('rb') as source:
    for block in iter(lambda:source.read(1024*1024),b''):sha.update(block)
report['snapshot_size']=path.stat().st_size;report['snapshot_sha256']=sha.hexdigest();mark('pickle_hashed')
del snapshot,streams,row,line
gc.collect();mark('references_released')
report['original_join_budget_sec']=20.;report['exceeds_original_join_budget']=report['phases']['references_released']>20.
(target/'timings.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
