"""Same actual failed frame, interleaved encoder CPU; not an engine verdict."""
import hashlib,importlib.util,json,marshal,pickle,statistics,time,uuid
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
source=root/'observer-postmortem-e5f0aea4/interrupted-freshness-32600a65-e38e-462b-a623-ae601a1dc254/first_failed_frame.json'
row=dict(kind='frame',value=json.loads(source.read_text()))
sys.path.insert(0,str(root.parents[2]/'scripts'))
import observer_journal_13_5 as capture_codec
encode_record=capture_codec.encode_record
target=root/('benchmark-observer-encoding-'+str(uuid.uuid4()));target.mkdir()
encoders=dict(json=lambda value:json.dumps(value,allow_nan=False),
    pickle=lambda value:pickle.dumps(value,protocol=5),marshal=lambda value:marshal.dumps(value,4),
    capture_checked=encode_record)
times={name:[] for name in encoders};sizes={}
for index in range(1000):
    for name in list(encoders)[index%len(encoders):]+list(encoders)[:index%len(encoders)]:
        start=time.thread_time_ns();payload=encoders[name](row);times[name].append(time.thread_time_ns()-start)
        sizes[name]=len(payload)
    if index==0:
        assert pickle.loads(encoders['pickle'](row))==row
        assert marshal.loads(encoders['marshal'](row))==row
summary={name:dict(mean_cpu_ms=statistics.mean(values)/1e6,p99_cpu_ms=sorted(values)[989]/1e6,
    max_cpu_ms=max(values)/1e6,encoded_bytes=sizes[name]) for name,values in times.items()}
report=dict(scope='interleaved_1000_actual_frame_no_ros_no_native_acceptance',source=str(source),
    python=__import__('sys').version,orjson_installed=importlib.util.find_spec('orjson') is not None,
    codec_sha256=hashlib.sha256(Path(capture_codec.__file__).read_bytes()).hexdigest(),
    results=summary)
(target/'result.json').write_text(json.dumps(report,indent=2));(target/'method.py').write_bytes(Path(__file__).read_bytes())
(target/'observer_journal_13_5.py').write_bytes(Path(capture_codec.__file__).read_bytes())
print(target,flush=True);print(json.dumps(report),flush=True)
