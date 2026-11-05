"""Build isolation and BT evidence checks, independent of ROS imports."""
from pathlib import Path

PROTECTED=('/home/jinho/ch13_reuse_r2_build','/home/jinho/ch13_reuse_r5_build',
 '/home/jinho/ch13_reuse_13_6_build','/home/jinho/ch13_reuse_13_6_guide_validation_v13_20261104')


def validate_build(value):
    path=Path(value).expanduser().resolve()
    for item in PROTECTED:
        protected=Path(item).resolve()
        if path==protected or path in protected.parents or protected in path.parents:
            raise ValueError('13.7 build overlaps protected install: '+str(path))
    return path


def lift_interrupt(progress,started_ns):
    if progress.get('task_phase')!='LIFT' or progress.get('manipulation_phase')!='EXECUTING':return None,False
    clock=progress.get('clock_ns',0)
    if started_ns is None:started_ns=clock
    return started_ns,clock-started_ns>=1_000_000_000


def verify_bt(data):
    p=data.get('port',{});events=p.get('events',[]);requested=p.get('requested',[])
    started=[e for e in events if e.get('event')=='started']
    session=data.get('session')
    checks=dict(actual_profile=data.get('profile')=='actual',session=bool(session),
        worker_joined=data.get('worker_joined') is True,
        worker_success=data.get('worker',{}).get('exit_code')==0,
        no_worker_error=not p.get('error'),closed=p.get('closed') is True,
        same_session=bool(started) and all(e.get('session')==session for e in started),
        goal_tracker_clean=not data.get('goals',{}).get('errors'))
    if data.get('case')=='normal':
        completed=p.get('completed',{});found=completed.get('find',{})
        sample=found.get('observation',{})
        checks.update(success=data.get('terminal')=='SUCCESS',
            ordered=requested==['navigate','find','pick','finish'],
            all_completed=all(k in completed for k in ('navigate','find','pick','finish')),
            original_capture=bool(sample.get('source_gids')) and sample.get('capture_ns',0)>0 and len(sample.get('rgb_sha256',''))==64,
            find_session=found.get('session')==session,no_cancel=not p.get('cancel_reason'))
    else:
        injections=[e for e in events if e.get('event')=='injection']
        stops=[e for e in events if e.get('event')=='navigation_terminal_and_settled']
        checks.update(aborted=data.get('terminal')=='ABORTED',injected=len(injections)==1,
            cancel_ack=any(data.get('goals',{}).get('cancel_acks',[])),
            actual_canceled_terminal=5 in data.get('goals',{}).get('terminals',[]),
            all_goals_drained=data.get('goals',{}).get('pending')==0,
            canceled=bool(p.get('cancel_reason')),no_pick_after_nav_cancel=('pick' not in requested if data.get('case')!='held_cancel' else True),
            actual_nav_stop=any(e.get('terminal')==5 and e.get('stationary_ready') and e.get('displacement_m',0)>.03 for e in stops) if data.get('case')!='held_cancel' else any(e.get('event')=='pick_canceled_and_settled' for e in events))
    return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks)


if __name__=='__main__':
    import sys
    print(validate_build(sys.argv[1]))
