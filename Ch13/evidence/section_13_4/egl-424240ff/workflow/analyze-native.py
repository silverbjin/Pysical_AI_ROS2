"""Derived metadata only; original trials are never rewritten."""
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics

root = Path(os.environ['CH13_EGL_EVIDENCE'])
rows = []
for entry in (root/'matrix-progress.jsonl').read_text().splitlines():
    progress = json.loads(entry)
    folder = root/progress['label']
    result = json.loads((folder/'result.json').read_text())
    row = dict(label=progress['label'],run_id=result['run_id'],status=result['status'],
               failed_checks=progress['failed_checks'],cleanup_confirmed=progress['cleanup_confirmed'],
               checks=result['checks'],errors=result.get('errors'),
               geometry=result.get('geometry'),tracking=result.get('tracking_metrics'))
    if (folder/'trace_summary.json').is_file():
        trace = json.loads((folder/'trace_summary.json').read_text())
        row['trace'] = {k:trace.get(k) for k in ('analysis_status','native_boundary','counts','collector','errors','segments','gate_losses')}
        gaps = trace.get('target_gaps_ns', [])
        row['target_gap_ms'] = dict(count=len(gaps),median=statistics.median(gaps)/1e6 if gaps else None,
                                    maximum=max(gaps)/1e6 if gaps else None)
        native = defaultdict(list)
        outcomes = defaultdict(Counter)
        raw = []
        for line in (folder/'trace.jsonl').read_text().splitlines():
            value = json.loads(line)['record']
            raw.append(value)
            outcomes[value['stage']][value['outcome']] += 1
            if value['stage'] == 'camera' and value['outcome'] == 'PUBLISHED':
                key = tuple(value[k] for k in ('producer_id','boot_id','clock_id','local_epoch'))
                native[key].append(value['times_ns']['rgb_publish_start'])
        intervals = []
        for times in native.values():
            times.sort()
            intervals.extend(b-a for a,b in zip(times,times[1:]))
        row['observed_native_publish_interval_ms'] = dict(count=len(intervals),
            median=statistics.median(intervals)/1e6 if intervals else None,
            maximum=max(intervals)/1e6 if intervals else None,
            note='Received native trace events only; dropped records can enlarge intervals.')
        row['outcomes'] = {k:dict(v) for k,v in outcomes.items()}
        contexts = []
        for loss in trace.get('gate_losses', []):
            matching = defaultdict(list)
            for value in raw:
                if (value['capture_ns'] == loss['capture_ns'] and
                        value['source_frame'] == loss['source_frame'] and
                        value['stage'] in ('camera','detector','fusion')):
                    matching[value['stage']].append(value)
            contexts.append(dict(loss=loss,exact_capture_stage_candidates=dict(matching),
                note='Original metadata candidates only; no nearest-capture substitution. '
                     'Ambiguous candidates are not resolved by this context display.'))
        row['gate_contexts'] = contexts
    row['source_head'] = result.get('source_head')
    row['result_sha256'] = hashlib.sha256((folder/'result.json').read_bytes()).hexdigest()
    rows.append(row)
output = root/'native-analysis.json'
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(dict(trials=rows,product_status='FAIL' if any(v['status']!='PASS' for v in rows) else 'PARTIAL',
    note='Derived from completed trials only. No assertion that prescribed matrix is complete. '
         'Trace coverage PARTIAL is not product PASS; original results/hashes are unchanged.'),indent=2)+'\n')
for row in rows:
    print(json.dumps({k:row[k] for k in ('label','status','failed_checks','cleanup_confirmed')}))
