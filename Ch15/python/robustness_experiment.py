"""B reference is reused; three actual one-variable MuJoCo perturbations."""
import argparse,json,hashlib
from pathlib import Path
from pid_experiment import run_case,plot_cases
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);base=json.loads((out/'B_tuned.json').read_text())
    assert base['kp']==25 and base['kd']==9.5 and base['inertia_kg_m2']==1 and base['damping_nm_s_rad']==.5 and base['delay_steps']==0
    h=hashlib.sha256((out/'B_tuned.csv').read_bytes()).hexdigest()
    cases={}
    for name,kw in [('inertia_plus10pct',dict(inertia=1.1)),('damping_half',dict(damping=.25)),('delay_20ms',dict(delay_steps=4))]:
        cases[name]=run_case(a.model,out,name,25.,9.5,**kw)
    assert hashlib.sha256((out/'B_tuned.csv').read_bytes()).hexdigest()==h
    checks={name:bool(x['finite'] and x['limit_violation']==0 and x['samples']==800 and x['kp']==25 and x['kd']==9.5) for name,x in cases.items()}
    # delay witness: exact four zero leading commands and delayed clipped control thereafter
    import csv
    with (out/'delay_20ms.csv').open() as f:rows=list(csv.DictReader(f))
    applied=[float(x['applied_nm']) for x in rows];clipped=[float(x['clipped_nm']) for x in rows]
    checks['exact_delay']=applied==[0.]*4+clipped[:-4]
    checks['one_variable_inertia']=abs(cases['inertia_plus10pct']['inertia_kg_m2']-1.1)<1e-9 and cases['inertia_plus10pct']['damping_nm_s_rad']==.5 and cases['inertia_plus10pct']['delay_steps']==0
    checks['one_variable_damping']=cases['damping_half']['inertia_kg_m2']==1 and cases['damping_half']['damping_nm_s_rad']==.25 and cases['damping_half']['delay_steps']==0
    checks['one_variable_delay']=cases['delay_20ms']['inertia_kg_m2']==1 and cases['delay_20ms']['damping_nm_s_rad']==.5 and cases['delay_20ms']['delay_steps']==4
    plot_cases(out,['B_tuned',*cases],'robustness.png')
    result=dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,baseline_reused_sha256=h,baseline=base,cases=cases)
    (out/'robustness_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
