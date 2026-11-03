"""Independent physics-evidence grading; never a control/vision input."""
import numpy as np


def assess_pick(rows):
    failures=[]
    try:
        if len(rows)<3:raise ValueError('insufficient physical evidence')
        times=np.array([r['sim_s'] for r in rows],dtype=float)
        if not np.isfinite(times).all() or np.any(np.diff(times)<=0):raise ValueError('nonadvancing physical time')
        for row in rows:
            if (np.asarray(row['target']).shape!=(3,) or np.asarray(row['relative_tcp']).shape!=(3,) or
                    not all(np.isfinite(np.asarray(value,dtype=float)).all() for value in
                            (row['target'],row['relative_tcp'],list(row['target_contact_N'].values())))):
                raise ValueError('nonfinite or malformed physical state/contact')
        baseline=[r['target'][2] for r in rows if r['phase']=='PRE_GRASP']
        hold=[r for r in rows if r['phase']=='HOLD']
        grasp=[r for r in rows if r['phase']=='CLOSE' and all(r['target_contact_N'].get(j,0.)>.005 for j in ('link7','link8'))]
        if not baseline or len(hold)<2:raise ValueError('pre-grasp baseline and measured hold required')
        start_z=float(np.median(baseline));height=np.array([r['target'][2]-start_z for r in hold])
        relative=np.asarray([r['relative_tcp'] for r in hold],dtype=float)
        if not np.isfinite(height).all() or not np.isfinite(relative).all():raise ValueError('nonfinite physical state')
        duration=float(hold[-1]['sim_s']-hold[0]['sim_s'])
        slip=float(np.max(np.linalg.norm(relative-relative[0],axis=1)))
        contact_fraction=float(np.mean([all(r['target_contact_N'].get(j,0.)>.005 for j in ('link7','link8')) for r in hold]))
        if min(height)<.09:failures.append('LIFT_HEIGHT')
        if duration<2.:failures.append('HOLD_DURATION')
        if slip>.02:failures.append('RELATIVE_SLIP')
        if not grasp or contact_fraction<.9:failures.append('DUAL_FINGER_CONTACT')
        return dict(result='FAIL' if failures else 'PASS',failures=failures,baseline_z_m=start_z,
                    minimum_lift_m=float(min(height)),maximum_lift_m=float(max(height)),hold_sim_s=duration,
                    relative_slip_m=slip,dual_contact_fraction=contact_fraction)
    except (ValueError,TypeError,KeyError) as error:
        return dict(result='FAIL',failures=['INVALID_OR_INCOMPLETE_PHYSICS_EVIDENCE'],reason=str(error))


def assess_held_cancel(rows):
    """Hold after actual cancellation; deliberately no successful lift claim."""
    try:
        hold=[r for r in rows if r['phase']=='HOLD']
        if len(hold)<2:raise ValueError('measured post-cancel hold absent')
        times=np.array([r['sim_s'] for r in hold]);points=np.array([r['target'] for r in hold])
        relative=np.array([r['relative_tcp'] for r in hold])
        forces=np.array([[r['target_contact_N'].get(f,0.) for f in ('link7','link8')] for r in hold])
        if not all(np.isfinite(a).all() for a in (times,points,relative,forces)):raise ValueError('nonfinite hold evidence')
        if np.any(np.diff(times)<=0):raise ValueError('nonadvancing hold time')
        duration=float(times[-1]-times[0]);drop=float(points[0,2]-points[:,2].min())
        slip=float(np.linalg.norm(relative-relative[0],axis=1).max());dual=float(np.mean(np.all(forces>.005,axis=1)))
        good=duration>=2. and drop<=.005 and slip<=.02 and dual>=.9
        return dict(result='PASS' if good else 'FAIL',scope='held-object cancellation safety, not physical pick completion',
                    hold_sim_s=duration,maximum_drop_m=drop,relative_slip_m=slip,dual_contact_fraction=dual)
    except (ValueError,TypeError,KeyError,IndexError) as error:
        return dict(result='FAIL',reason=str(error))
