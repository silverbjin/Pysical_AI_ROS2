"""Trusted local diagnostic subset. Never modifies/promotes the failed trial."""
import hashlib,json,pickle,sys,uuid
from collections import Counter
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
from native_observer_13_5 import read_records
root=Path(sys.argv[1]);base=Path(sys.argv[2]);closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text());fault=report['first_fault']
phase=fault['phase_context']['_phase_start']
first=next(r for r in report['decision_cost_trace'] if r.get('decision_ros_ns')==phase)
start=first['started_wall_ns']-600_000_000;end=fault['wall_ns'];packets=[]
keys={'joints','imu','contacts','body','scan','carry','guard_state','applied_reference'}
source=root/'observations.cdr';sha=hashlib.sha256()
with source.open('rb') as stream:
    for block in iter(lambda:stream.read(4*1024*1024),b''):sha.update(block)
with source.open('rb') as stream:
    for row in read_records(stream):
        m=row['meta']
        if m['kind']=='packet' and m['key'] in keys and start<=m['received_ns']<=end:
            packets.append((m['received_ns']-start,m['key'],row['payload'],m['sequence']))
from builtin_interfaces.msg import Time
from rosgraph_msgs.msg import Clock
from rclpy.serialization import serialize_message
with (root/'control_clock.jsonl').open() as stream:
    for line in stream:
        row=json.loads(line)
        if row.get('event')=='publish' and start<=row['published_wall_ns']<=end:
            capture=row['capture_ns'];msg=Clock(clock=Time(sec=capture//10**9,nanosec=capture%10**9))
            packets.append((row['published_wall_ns']-start,'clock',serialize_message(msg),None))
packets.sort(key=lambda r:r[0]);assert packets and set(r[1] for r in packets)==keys|{'clock'}
out=base/('contention-window-'+str(uuid.uuid4()));out.mkdir()
fixture=out/'trusted-packets.pickle';fixture.write_bytes(pickle.dumps(packets,protocol=5))
value=dict(scope=__doc__,original_trial=str(root),original_cdr_sha256=sha.hexdigest(),
    controller_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    start_wall_ns=start,end_wall_ns=end,duration_ns=end-start,packets=len(packets),
    counts=dict(Counter(row[1] for row in packets)),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    scope_notes='CDR message bytes retained; control Clock messages reconstructed only from recorded original capture_ns, never now. New DDS delivery is diagnostic only; omitted TF/native controls and original velocity channel are not simulated. No engine acceptance.')
(out/'method.py').write_bytes(Path(__file__).read_bytes());(out/'manifest.json').write_text(json.dumps(value,indent=2))
print(json.dumps(dict(output=str(out),**value)))
