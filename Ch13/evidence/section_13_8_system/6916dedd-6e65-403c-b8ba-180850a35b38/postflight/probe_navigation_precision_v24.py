"""Actual navigation-only precision regression, not a complete13.8 mission."""
import json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);manifest=Path(sys.argv[3])
assert not out.exists(), 'new evidence UUID required'
subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(manifest)],check=True)
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level1_floor'
sys.path.insert(0,str(root/'Ch13/scripts/reuse_13_5'))
from run_navigation_probe import main as navigate
class Probe:
    def poll(self): pass
    def ready(self,*,node,until,snapshot):
        from rcl_interfaces.srv import GetParameters
        client=node.create_client(GetParameters,'/controller_server/get_parameters')
        try:
            assert until(client.service_is_ready,3.)
            names=['goal_checker.xy_goal_tolerance','goal_checker.yaw_goal_tolerance','goal_checker.stateful']
            future=client.call_async(GetParameters.Request(names=names));assert until(future.done,3.)
            values=future.result().values
            record=dict(zip(names,[values[0].double_value,values[1].double_value,values[2].bool_value]))
            (out/'actual_controller_parameters.json').write_text(json.dumps(record,indent=2)+'\n')
            assert record['goal_checker.xy_goal_tolerance']==.015,record
        finally:node.destroy_client(client)
    def track_goal(self,*args): pass
    def cancel_requested(self): return False
    def navigation_complete(self,*args): pass
    def await_step(self,*args): pass
result=navigate(['--repo-root',str(root),'--evidence',str(out),'--case','free'],orchestration=Probe())
assert result==0, 'parameter/startup/navigation failure; preserve summary, no terminal verifier on incomplete admission'
subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_5/verify_navigation.py'),str(out)],check=True)
summary=json.loads((out/'navigation_summary.json').read_text())
report=dict(result='PASS' if result==0 and summary['actual_goal_error_m']<.03 else 'FAIL',
    actual_goal_error_m=summary['actual_goal_error_m'],target=summary['target'],
    scope='one unloaded forward navigation goal; no return rotation, pick or transport robustness claim',
    source_manifest_sha256=__import__('hashlib').sha256(manifest.read_bytes()).hexdigest())
(out/'precision_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert report['result']=='PASS'