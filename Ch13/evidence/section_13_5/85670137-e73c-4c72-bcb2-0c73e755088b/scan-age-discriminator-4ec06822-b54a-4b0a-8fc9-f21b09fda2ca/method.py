"""Closed-trial capture/receipt budget discriminator; no live runtime work."""
from pathlib import Path
import json,hashlib,uuid

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-gazebo-ae04a225-410f-4f76-8c49-f4992703422e'
closed=json.loads((trial/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
frames=json.loads((trial/'all_frames.json').read_text())['frames'];seen=set();rows=[]
for f in frames:
    s=f['samples']['scan']
    if 40_800_000_000<=f['ros_ns']<=42_000_000_000 and s and s['sequence'] not in seen:
        seen.add(s['sequence']);rows.append(dict(frame_ros_ns=f['ros_ns'],frame_wall_ns=f['wall_ns'],
            scan_ros_ns=s['stamp_ns'],scan_received_ns=s['received_ns']))
gaps=[dict(from_ros=a['scan_ros_ns'],to_ros=b['scan_ros_ns'],
    wall_gap_ns=b['scan_received_ns']-a['scan_received_ns'],
    effective_capture_ratio=(b['scan_ros_ns']-a['scan_ros_ns'])/(b['scan_received_ns']-a['scan_received_ns']))
    for a,b in zip(rows,rows[1:])]
stop=json.loads((trial/'controller_report.json').read_text())['first_stop']
sample=stop['samples']['scan']
out=base/('scan-age-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='independent_observer_and_crawl_selected_cache_not_guard_callback_trace',
    trial=trial.name,source_manifest_sha256=hashlib.sha256((trial/'source_manifest.json').read_bytes()).hexdigest(),
    input_all_frames_sha256=hashlib.sha256((trial/'all_frames.json').read_bytes()).hexdigest(),
    rows=rows,gaps=gaps,worst=max(gaps,key=lambda g:g['wall_gap_ns']),
    controller_first_stop=dict(reason=stop['reason'],ros_ns=stop['ros_ns'],wall_ns=stop['wall_ns'],
        selected_scan_capture_ns=sample['stamp_ns'],selected_scan_received_ns=sample['received_ns'],
        measured_scan_wall_age_ns=stop['wall_ns']-sample['received_ns']),
    safety_limit_ns=300_000_000,
    new_capture_schedule_hz=20.,nominal_period_wall_s_at_measured_slowdown=.05/max(gaps,key=lambda g:g['wall_gap_ns'])['effective_capture_ratio'],
    caveats=['receipt-gap ratio includes engine scheduling/render/transport; it is not a pure physics CPU profile',
        'This identifies an acquisition-to-wall-lease budget failure, not a unique render/backend CPU cause',
        '20Hz is a proposed actual acquisition schedule, not a guarantee of future deadline compliance',
        'No original header or historical result is changed'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),worst=value['worst'],first_stop=value['controller_first_stop'])),flush=True)
