"""Reuse body transport edge equations, stream input instead of multi-GB read_text."""
import json,uuid
from pathlib import Path
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
root=native/'native-g2-mujoco-e5f0aea4-bbea-427d-8d25-f020bfbe78fd'
target=native/('interrupted-body-window-'+str(uuid.uuid4()));target.mkdir()
streams={key:[] for key in ('body_source','body_transport')}
with (root/'observations.jsonl').open('rb') as source:
    for line in source:
        if not line.startswith((b'{"kind": "body_source",',b'{"kind": "body_transport",')):continue
        row=json.loads(line);streams[row['kind']].append(row['value'])
original={row['stamp_ns']:row for row in streams['body_source']}
edges=[]
for row in streams['body_transport']:
    if not 706_100_000_000<=row['stamp_ns']<=706_800_000_000:continue
    incoming=original.get(row['stamp_ns'])
    detail=dict(row)
    if incoming:
        detail.update(native_message=incoming,
            source_rmw_delivery_ms=(incoming['rmw_received_system_ns']-incoming['source_system_ns'])/1e6,
            source_probe_dispatch_ms=(incoming['callback_system_ns']-incoming['rmw_received_system_ns'])/1e6,
            source_to_adapter_publication_ms=(row['source_system_ns']-incoming['source_system_ns'])/1e6,
            output_rmw_delivery_ms=(row['rmw_received_system_ns']-row['source_system_ns'])/1e6,
            output_probe_dispatch_ms=(row['callback_system_ns']-row['rmw_received_system_ns'])/1e6)
    edges.append(detail)
report=dict(scope='postmortem_matching_capture_edges_no_trace_implies_no_callback_claim',
    original=str(root),window=edges,
    source_window=[row for row in streams['body_source'] if 706_100_000_000<=row['stamp_ns']<=706_800_000_000])
(target/'body-window.json').write_text(json.dumps(report,indent=2))
print('BODY_WINDOW',target,flush=True)
print(json.dumps([dict(capture_ns=row['stamp_ns'],receipt_ns=row['received_ns'],
    adapter_ms=row.get('source_to_adapter_publication_ms'),output_dispatch_ms=row.get('output_probe_dispatch_ms')) for row in edges]),flush=True)
