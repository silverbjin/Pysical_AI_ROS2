"""Startup-only diagnostic; no arm, navigation enable, or action goal admission."""
import argparse,json,os,subprocess,sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--freeze',required=True,type=Path)
    args=parser.parse_args();root=args.repo_root.resolve();out=args.evidence.resolve()
    if out.exists():raise ValueError('new diagnostic evidence directory required')
    out.mkdir(parents=True);scripts=root/'Ch13/scripts';run=out/'run'
    def checked(script,*values,log):
        with (out/log).open('w') as stream:
            subprocess.run([sys.executable,str(script),*map(str,values)],stdout=stream,stderr=subprocess.STDOUT,check=True)
    checked(scripts/'reuse_13_6/freeze_runtime.py','verify',args.freeze.resolve(),log='freeze_audit.json')
    checked(scripts/'reuse_13_6/audit_install.py',out/'install_audit.json',log='audit.log')
    checked(scripts/'reuse_13_5/inspect_r2_residuals.py',out/'pre_residual.json',log='pre_residual.log')
    os.environ['CH13_REUSE_STARTUP_TRACE']=str(run)
    sys.path.insert(0,str(scripts/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    def forbidden_handoff(**context):raise AssertionError('startup-only diagnostic reached manipulation')
    rc=navigate(['--repo-root',str(root),'--evidence',str(run),'--case','vision','--vision-hz','15'],
                handoff=forbidden_handoff,startup_only=True)
    checked(scripts/'reuse_13_5/inspect_r2_residuals.py',out/'post_residual.json',log='post_residual.log')
    summary=json.loads((run/'navigation_summary.json').read_text());engine=json.loads((run/'engine.json').read_text())
    rows=[json.loads(s) for s in (run/'engine_observations.jsonl').read_text().splitlines()]
    assert summary.get('startup_only') and not summary['events']
    assert all(n in ('navigation/idle','platform/shutdown') for n in summary['startup_service_calls'])
    assert all(r['mode']!='ARMED' and r['vx']==r['wz']==0 for r in rows),'motion admission during diagnostic'
    assert not engine['manipulation']['arm_events'],'arm/gripper action during diagnostic'
    assert all(engine[k] for k in ('normal_shutdown_requested','rx_joined','camera_worker_joined','upstream_threads_joined'))
    assert not summary['remaining_launch_pids'] and summary['clean_launch_exits']==len(summary['owned_launch_pids'])
    for name in ('gateway','navigation'):assert (run/(name+'_startup_trace.json')).exists()
    value=dict(result=summary['result'],startup_only=True,no_motion_admission=True,normal_recovery=True,
               gateway_fault=summary['gateway_last'].get('fault'),navigation_fault=summary['navigation_last'].get('fault'))
    (out/'startup_verification.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value,indent=2))
    return rc


if __name__=='__main__':sys.exit(main())
