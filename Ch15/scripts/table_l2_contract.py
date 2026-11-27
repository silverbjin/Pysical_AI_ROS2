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

def goal_trace_matches(audit,phases):
    """Exactly two actual Nav2 UUIDs must match the physical phase evidence."""
    try:
        expected=[{'goal_id':p['goal_id'],'terminal':4} for p in phases[:2]]
        return (len(phases)==4 and [p['phase'] for p in phases]==['survey_setup','entry_travel','clockwise_arc','straight']
            and all(p.get('terminal')==4 and p.get('settled') is True for p in phases[:2])
            and all(p.get('ready') is True for p in phases[2:])
            and all(len(x['goal_id'])==32 and int(x['goal_id'],16)>=0 for x in expected)
            and expected[0]['goal_id']!=expected[1]['goal_id']
            and audit['pending']==0 and audit['errors']==[] and audit['terminals']==[4,4]
            and audit['rows']==expected)
    except (KeyError,TypeError,ValueError,IndexError):return False
