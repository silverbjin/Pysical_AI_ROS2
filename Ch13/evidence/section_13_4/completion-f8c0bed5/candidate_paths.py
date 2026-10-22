"""Join capture evidence without treating missing telemetry as a missing callback."""
from collections import Counter
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1]).resolve()
output = folder/'candidate-paths.json'
result = json.loads((folder/'result.json').read_text())
observations = json.loads((folder/'observations.json').read_text())
rows = {}
sequences = {'fusion': [], 'detector_input': []}

def capture(key):
    return rows.setdefault(key, dict(capture_ns=key, ingress=[], selection=[], worker=[],
                                    traces=[], target_receipts=[]))

for item in observations.get('diagnostics', []):
    key = item.get('capture_ns')
    if key is None:
        continue
    row = capture(key)
    if item['status'] == 'CANDIDATE':
        sequences['fusion'].append(item['sequence'])
        row['selection'].append({k: v for k, v in item.items() if k not in ('status', 'run_id')})
    elif item['status'] in ('INPUT_RECEIVED', 'INPUT_REJECTED'):
        sequences['detector_input'].append(item['sequence'])
        row['ingress'].append(item)

trace_path = folder/'trace.jsonl'
if trace_path.exists():
    for line in trace_path.read_text().splitlines():
        record = json.loads(line)['record']
        key = record.get('capture_ns')
        if key is not None:
            capture(key)['traces'].append(dict(stage=record['stage'],
                outcome=record['outcome'], times_ns=record['times_ns'],
                ros_now_ns=record.get('ros_now_ns'),
                local_epoch=record['local_epoch'], producer_id=record['producer_id']))
for item in observations.get('tracks', []):
    capture(item['capture_ns'])['target_receipts'].append(item)

counts = Counter()
for row in rows.values():
    events = [item['event'] for item in row['selection']]
    if 'SLOT_OVERWRITTEN' in events:
        disposition = 'SUBMITTED_THEN_OVERWRITTEN'
    elif 'SUBMITTED' in events:
        disposition = 'SUBMITTED'
    elif 'DETECTION_RECEIVED' in events:
        terminal = [name for name in events if name in
                    ('EXPIRED_OR_OLD', 'OLD_OR_DUPLICATE', 'SUPERSEDED', 'CAPACITY_EVICTED')]
        disposition = terminal[-1] if terminal else 'PENDING_OR_PARTIAL_TELEMETRY'
    else:
        disposition = 'NO_FUSION_CANDIDATE_OBSERVED'
    row['disposition'] = disposition
    counts[disposition] += 1
    row['worker'] = [item for item in row['selection'] if item['event'].startswith('WORKER_')]

coverage = {}
for producer, values in sequences.items():
    unique = sorted(set(values))
    coverage[producer] = dict(observed=len(unique), first=min(unique) if unique else None,
        last=max(unique) if unique else None,
        internal_gaps=[[a+1, b-1] for a, b in zip(unique, unique[1:]) if b > a+1])
value = dict(run_id=result['run_id'], source_result_status=result['status'],
    counts=dict(counts), diagnostic_sequences=coverage, rows=sorted(rows.values(), key=lambda r:r['capture_ns']),
    limitations=['No observed candidate is not proof that its callback did not run.',
        'Trace/status delivery can be partial; initial/tail totals are not inferred.',
        'Detector newest-slot throttling can omit intermediate images intentionally.',
        'Submitted jobs can expire or be overwritten; read explicit events and outcomes.',
        'This derived file never changes the native result or acceptance checks.'])
with output.open('x') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(run_id=value['run_id'], counts=value['counts'], coverage=coverage)))
