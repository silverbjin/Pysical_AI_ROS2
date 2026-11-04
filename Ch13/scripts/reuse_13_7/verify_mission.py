import json,sys,subprocess
from pathlib import Path
from ch13_mission_orchestration.tools import verify_bt
root=Path(__file__).resolve().parents[3];case=Path(sys.argv[1]);run=case/'run'
data=json.loads((run/'bt_summary.json').read_text());result=verify_bt(data)
nav=json.loads((run/'navigation_summary.json').read_text())
result['checks']['owned_lifecycle']=(nav.get('result')=='PASS' and not nav.get('remaining_launch_pids') and nav.get('planner_stopped_before_engine') is True and nav.get('clean_launch_exits')==len(nav.get('owned_launch_pids',[])))
for name in ('pre_residual','post_residual'):
    result['checks'][name]=json.loads((case/(name+'.json')).read_text()).get('result')=='PASS'
if data['case'] in ('normal','held_cancel'):
    script=root/'Ch13/scripts/reuse_13_6/verify_pick.py'
    with (case/'physical_verification.log').open('w') as log:
        if data['case']=='normal':code=subprocess.call([sys.executable,str(script),str(case)],stdout=log,stderr=subprocess.STDOUT)
        else:
            sys.path.insert(0,str(script.parent));from verify_pick import verify
            try:verify(case,held_cancel=True);code=0
            except Exception:__import__('traceback').print_exc(file=log);code=1
    result['checks']['physical_pick']=code==0
else:
    # Existing navigation calculator verifies actual motion/stop/forces/join.
    script=root/'Ch13/scripts/reuse_13_6/verify_navigation.py'
    with (case/'physical_verification.log').open('w') as log:
        code=subprocess.call([sys.executable,str(script),str(case)],stdout=log,stderr=subprocess.STDOUT)
    result['checks']['physical_stop']=code==0
result['result']='PASS' if all(result['checks'].values()) else 'FAIL'
(case/'mission_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
sys.exit(0 if result['result']=='PASS' else 1)
