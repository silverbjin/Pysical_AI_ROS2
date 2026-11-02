"""Bulk evidence must stay exact without the expanded pretty-print copy.

Capture stamps, original local receipts and full frame counts are data, not
formatting. Invalid numeric evidence must never replace an existing verdict.
"""
import json
import math
import pytest
import run_navigation_13_5 as runner


@pytest.mark.parametrize('name',['frames.json','all_frames.json','native_controls.json'])
def test_bulk_evidence_is_lossless_and_uses_less_recording_space(tmp_path,name):
    frame=dict(source_header=dict(frame_id='camera_optical_frame',sec=71,nanosec=999999999),
        first_received_monotonic_ns=2**58+17,phase='SWING',fault=None,accepted=True,
        label='컵',values=[-0.0,1.2345678901234567,1e-12,-1e-12,1e300]*4)
    data=dict(scope='original_samples',frames=[frame for _ in range(256)])
    path=tmp_path/name;runner.save(path,data)
    encoded=path.read_bytes();decoded=json.loads(encoded)
    assert decoded==data
    assert len(decoded['frames'])==256
    assert decoded['frames'][0]['first_received_monotonic_ns']==2**58+17
    assert math.copysign(1.,decoded['frames'][0]['values'][0])==-1.
    expanded=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode()
    assert len(encoded)<.7*len(expanded), 'bulk evidence still stores an expanded pretty-print copy'


@pytest.mark.parametrize('name',['result.json','teardown.json','frames.json'])
@pytest.mark.parametrize('invalid',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_evidence_never_truncates_a_previous_result(tmp_path,name,invalid):
    path=tmp_path/name;original=b'{"status":"FAIL","complete":false}\n';path.write_bytes(original)
    with pytest.raises(ValueError):runner.save(path,dict(sample=invalid))
    assert path.read_bytes()==original


def test_small_verdict_metadata_keeps_existing_readable_representation(tmp_path):
    value=dict(status='FAIL',checks=dict(normal_engine_exit=False),errors=['original failure'])
    path=tmp_path/'result.json';runner.save(path,value)
    assert path.read_text()==json.dumps(value,indent=2,allow_nan=False)+'\n'
