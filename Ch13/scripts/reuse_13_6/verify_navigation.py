"""Official13.6 navigation verdict: unchanged physical metrics, explicit fault contract."""
import argparse,hashlib,json,subprocess,sys,traceback
from pathlib import Path
from ch13_manipulation_reuse.navigation_acceptance import fault_contract

ROOT=Path(__file__).resolve().parents[3]


def verify(folder,output):
    run=folder/'run'
    legacy_output=output.with_name(output.stem+'_physical_metrics.json')
    legacy_log=output.with_name(output.stem+'_physical_metrics.log')
    assert not legacy_output.exists() and not legacy_log.exists(),'preserve previous calculations'
    helper=ROOT/'Ch13/scripts/reuse_13_5/verify_navigation.py'
    legacy=subprocess.run([sys.executable,str(helper),str(run),str(legacy_output)],capture_output=True,text=True)
    legacy_log.write_text(legacy.stdout+legacy.stderr)
    measured=json.loads(legacy_output.read_text())
    checks=dict(measured['checks'])
    assert measured['gate']=='section_13_5_edu_stop_v2'
    assert 'platform_no_unexpected_fault' in checks
    assert measured['result']==('PASS' if all(checks.values()) else 'FAIL')
    assert legacy.returncode==(0 if measured['result']=='PASS' else 1),'physical calculator failed unexpectedly'
    old_fault_check=checks.pop('platform_no_unexpected_fault')
    summary=json.loads((run/'navigation_summary.json').read_text())
    engine=json.loads((run/'engine.json').read_text())
    rows=[json.loads(line) for line in (run/'engine_observations.jsonl').read_text().splitlines()]
    checks['platform_fault_contract']=fault_contract(summary,engine,rows)
    checks['post_residual']=json.loads((folder/'post_residual.json').read_text())['result']=='PASS'
    return dict(result='PASS' if all(checks.values()) else 'FAIL',revision='13_6_navigation_formal_v1',
                case=summary['case'],checks=checks,metrics=measured['metrics'],
                legacy_fault_empty_check=old_fault_check,
                physical_calculator_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
                fault_evidence=dict(injection=summary.get('raw_loss_injection'),
                    gateway=summary.get('gateway_last',{}).get('fault_details'),platform=engine.get('fault_details')))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();output=args.output or args.folder/'navigation_verification.json'
    if output.exists():raise ValueError('use a new verdict filename; preserve original results')
    try:result=verify(args.folder,output)
    except Exception:result=dict(result='FAIL',revision='13_6_navigation_formal_v1',error=traceback.format_exc())
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if result['result']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
