"""Link every failed body sample to its original DDS transport timestamps."""
import hashlib,json,sys
from pathlib import Path
here=Path(__file__).parent;root=Path(sys.argv[1])
bad=[json.loads(line) for line in (here/'all_failures.jsonl').open()]
keys={(row['capture_ns'],row['first_receipt_ns']) for row in bad if row.get('reason')}
matches=[];count=0;sha=hashlib.sha256()
with (root/'observations.jsonl').open('rb') as source:
    for line in source:
        sha.update(line)
        if not line.startswith(b'{"kind": "body_transport",'):continue
        row=json.loads(line)['value'];count+=1
        if (row['stamp_ns'],row['received_ns']) not in keys:continue
        item=dict(row)
        if all(row.get(key) for key in ('source_system_ns','rmw_received_system_ns','callback_system_ns')):
            item['publisher_to_rmw_ms']=(row['rmw_received_system_ns']-row['source_system_ns'])/1e6
            item['rmw_to_callback_ms']=(row['callback_system_ns']-row['rmw_received_system_ns'])/1e6
        matches.append(item)
value=dict(scope='original_wire_transport_match_not_clock_repair',source_sha256=sha.hexdigest(),
    transport_records=count,failed_capture_receipt_keys=sorted(keys),matches=matches,
    missing_keys=sorted(keys-{(row['stamp_ns'],row['received_ns']) for row in matches}))
assert value['source_sha256']==json.loads((here/'freshness.json').read_text())['source_sha256']
with (here/'body_transport.json').open('x') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
