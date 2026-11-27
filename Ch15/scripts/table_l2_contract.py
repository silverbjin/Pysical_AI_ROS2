"""Pure evidence predicates for Ch15 basic mission. Not a motion simulator."""
from collections import Counter

N='/ch13/reuse'
TOPICS=('/clock','/tf','/tf_static','/start_mission',N+'/joint_states',N+'/odometry',
        N+'/engine_state',N+'/scan',N+'/nav_cmd',N+'/cmd_vel_safe',
        N+'/vision/observation',N+'/vision/health',N+'/manipulation/status',
        N+'/navigation/status',N+'/validation/bt_log')

def bag_checks(counts,metadata_counts,starts,nonzero,success,discovered):
    return dict(exact_allowlist=set(counts)==set(TOPICS)==set(metadata_counts),
        counts_match=dict(counts)==dict(metadata_counts),
        all_nonempty=all(counts.get(t,0)>0 for t in TOPICS),
        discovery_before_start=set(discovered)==set(TOPICS),
        start_once=len(starts)==1,actual_motion=bool(nonzero),
        motion_after_start=bool(len(starts)==1 and nonzero and min(nonzero)>=starts[0]),
        terminal_recorded=bool(success and nonzero and max(success)>=max(nonzero)))

def goal_audit(rows):
    ids=[r.get('goal_id') for r in rows]
    errors=[]
    if any(not isinstance(i,str) or len(i)!=32 for i in ids):errors.append('missing UUID')
    if len(set(ids))!=len(ids):errors.append('duplicate UUID')
    if any(r.get('terminal') not in (4,5,6) for r in rows if 'terminal' in r):errors.append('invalid terminal')
    return dict(terminals=[r['terminal'] for r in rows if 'terminal' in r],
                errors=errors,pending=sum('terminal' not in r for r in rows),rows=rows)
