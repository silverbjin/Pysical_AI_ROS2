"""Counterfactual diagnosis of an immutable no-engine failure; no verdict promotion."""
import hashlib,json,sys,uuid
from pathlib import Path
from clock_convergence import ClockConvergence
source=Path(sys.argv[1]);base=source.parent.parent
closed=json.loads((source.parent/'session.json').read_text())
assert closed['restored'] and closed['foreground_sessions_closed'] and not closed['final_related_runtimes']
strict=ClockConvergence(deadline_ns=300_000_000_000)
equivalent=ClockConvergence(deadline_ns=300_000_000_000,allow_compensated_tick=True)
first_ready=None;count=0
with source.open() as stream:
    for line in stream:
        row=json.loads(line);count+=1;clock=row['clock'];raw=(row['raw_before_ns']+row['raw_after_ns'])//2
        strict.observe(raw,row['mono_ns'],row['real_ns'],clock['tick_us'])
        if first_ready is None and equivalent.observe(raw,row['mono_ns'],row['real_ns'],clock['tick_us'],
                freq_scaled_ppm=clock['freq_scaled_ppm'])=='READY':
            first_ready=dict(row=count,raw_ns=raw,elapsed_raw_ns=raw-equivalent.started,
                last_measured_ratio=equivalent.last_ratio,clock=clock)
assert strict.state=='FAULT' and first_ready is not None
out=base/('clock-encoding-replay-'+str(uuid.uuid4()));out.mkdir()
report=dict(scope=__doc__,original_failure=source.parent.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    rows=count,strict_final=strict.state,strict_reason=strict.reason,
    first_equivalent_ready=first_ready,engine_attempts=0,changes_clocks=False,
    limitation='Same historical observations only; not a new admission, host QPC witness or engine acceptance.')
(out/'method.py').write_bytes(Path(__file__).read_bytes());(out/'clock_convergence.py').write_bytes(Path(__file__).with_name('clock_convergence.py').read_bytes())
(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(output=str(out),**report)))
