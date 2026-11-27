"""Independent native engine evidence audit; never grants motion authority."""
import math
from arc_straight_profile import ANGLE,arc_point,wrap
from table_approach_contract import world


def engine_pose(row):
    q=row['qpos']
    return (q[0],q[1],math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2)))


def audit_phases(rows,phases,entry,target,engine):
    checks={};details=[]
    checks['engine_clean']=bool(engine.get('result')=='COMPLETED' and not engine.get('final_fault') and
        all(engine.get(k) is True for k in ('normal_shutdown_requested','rx_joined','camera_worker_joined','upstream_threads_joined')))
    checks['force_cap']=0<=engine.get('max_force_cap_ratio',float('inf'))<=1.000001
    checks['original_model']=engine.get('compiled_model_sha256')=='6ab165146bd617a8d99e6e71109bd140a7c9d56d30ddc91b3cf98e66914d25ff'
    for label,goal,gate,vmax,wmax in (('clockwise_arc',world((*arc_point(ANGLE),-ANGLE),entry),.03,.018,.10),('straight',target,.015,.035,.05)):
        found=[p for p in phases if p.get('phase')==label and p.get('ready') is True]
        if len(found)!=1:
            checks[label]=False;continue
        p=found[0];start=p['release_sim_ns']/1e9;end=p['end_sim_ns']/1e9;settle=p['settle_sim_ns']/1e9
        subset=[r for r in rows if start<=r['sim_s']<=end]
        close=min(rows,key=lambda r:abs(r['sim_s']-settle)) if rows else None
        if close is None:
            checks[label]=False;continue
        actual=engine_pose(close);reported=p['settled_pose']
        xy=math.dist(actual[:2],goal[:2]);yaw=abs(wrap(actual[2]-goal[2]));stamp_error=abs(close['sim_s']-settle)
        steps=[b['sim_s']-a['sim_s'] for a,b in zip(subset,subset[1:])]
        state_error=math.dist(actual[:2],reported[:2]);state_yaw=abs(wrap(actual[2]-reported[2]))
        checks[label]=bool(len(subset)>=100 and all(0<dt<=.05 for dt in steps) and
            all(r['mode']=='ARMED' and not r['fault'] and abs(r['vx'])<=vmax+1e-7 and abs(r['wz'])<=wmax+1e-7 for r in subset) and
            any(abs(r['vx'])>1e-6 for r in subset) and (label!='clockwise_arc' or any(r['wz']<-.01 for r in subset)) and
            stamp_error<=.020001 and state_error<=.003 and state_yaw<=.01 and xy<=gate and yaw<=.06 and not close['fault'])
        details.append(dict(phase=label,samples=len(subset),settled_engine_pose=actual,xy_error_m=xy,yaw_error_rad=yaw,
            timestamp_error_s=stamp_error,ros_pose_error_m=state_error,ros_yaw_error_rad=state_yaw,
            max_abs_vx=max((abs(r['vx']) for r in subset),default=0),max_abs_wz=max((abs(r['wz']) for r in subset),default=0)))
    return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,phases=details)
