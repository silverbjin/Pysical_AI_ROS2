"""Bounded actual-frame encoder comparison; no engine or acceptance verdict."""
import ast,hashlib,json,statistics,time,uuid
from pathlib import Path

repo=Path.cwd().resolve()
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
old=base/'recovery-52c0-09baf614-de45-4a37-af46-62d7f3239df4/source_snapshot/Ch13/scripts/run_navigation_13_5.py'
new=repo/'Ch13/scripts/run_navigation_13_5.py'
fixture=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g1-mujoco-2a6ad536-81df-40e7-8528-43d2bc198e71/frames.json')
def function(path):
    tree=ast.parse(path.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='save')
    namespace={'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace['save']
payload=fixture.read_bytes();original=json.loads(payload)
selected={key:(value[:512] if isinstance(value,list) else value) for key,value in original.items()}
normalized=json.dumps(selected,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
expected=hashlib.sha256(normalized).hexdigest();out=base/('bulk-json-benchmark-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
callbacks={'original':function(old),'compact':function(new)};rows=[]
for index,mode in enumerate(('original','compact','compact','original')):
    directory=out/str(index);directory.mkdir();target=directory/'frames.json'
    started_wall=time.perf_counter_ns();started_cpu=time.thread_time_ns()
    callbacks[mode](target,selected)
    cpu=time.thread_time_ns()-started_cpu;wall=time.perf_counter_ns()-started_wall
    encoded=target.read_bytes();decoded=json.loads(encoded)
    digest=hashlib.sha256(json.dumps(decoded,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert decoded==selected and digest==expected
    rows.append(dict(mode=mode,wall_ns=wall,cpu_ns=cpu,bytes=len(encoded),
        file_sha256=hashlib.sha256(encoded).hexdigest(),normalized_sha256=digest))
    assert target.resolve().is_relative_to(out.resolve())
    target.unlink();directory.rmdir()  # Derived copies only, after exact comparison and SHA.
report=dict(scope=__doc__,fixture=str(fixture),fixture_sha256=hashlib.sha256(payload).hexdigest(),
    original_source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    candidate_source_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
    list_counts={key:dict(original=len(value),selected=len(selected[key])) for key,value in original.items() if isinstance(value,list)},
    maximum_rows_per_list=512,normalized_sha256=expected,trials=rows,all_fields_values_and_order_preserved=True,
    derived_copies_removed_after_comparison=True,no_acceptance_claim=True)
report['by_mode']={mode:dict(mean_cpu_ns=statistics.mean(r['cpu_ns'] for r in rows if r['mode']==mode),
    mean_wall_ns=statistics.mean(r['wall_ns'] for r in rows if r['mode']==mode),bytes=next(r['bytes'] for r in rows if r['mode']==mode)) for mode in callbacks}
(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(output=str(out),**report),indent=2))
