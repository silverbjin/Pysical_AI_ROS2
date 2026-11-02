"""Owned G2 reference feasibility, distinct from measured contact stability."""
import numpy as np
from .leg_kinematics import ik_leg,thigh_trunk_clearance


def height_envelope(model,selected,points,targets,origins,neutral,floor,limits):
    p=np.array([points[f] for f in model.feet],dtype=float)
    if p.shape!=(4,3) or not np.isfinite(p).all():raise ValueError('reference envelope contacts')
    _,singular,vh=np.linalg.svd(np.column_stack((np.ones(4),p[:,1],-p[:,0])).T)
    null=vh[-1];index=model.feet.index(selected)
    if singular[-1]<1e-6 or abs(null[index])<1e-6:raise ValueError('reference envelope geometry')
    result={}
    for i,foot in enumerate(model.feet):
        current=float(targets[foot][2]);origin=origins[foot]
        if foot==selected:
            low=min(floor[foot],neutral[foot])-.002
            high=max(floor[foot]+limits['swing_height_m'],origin+limits['max_unload_height_m'])
        else:
            # correction = +C_i*F_selected*n_i/n_selected. Its sign is fixed
            # by this convex contact geometry; restoration returns to origin.
            edge=origin+float(np.sign(null[i]/null[index]))*limits['max_unload_height_m']
            low=min(origin,edge);high=max(origin,edge)
        result[foot]=(float(min(low,current)),float(max(high,current)))
    return result


def reference_constraints(model,limits,joints,body,targets,envelope,*,selected,future_targets):
    """Aggregate fixed-size residuals over independently owned leg references.

    One nominal joint map feeds ONE mass evaluation in the caller. Extra IK
    samples only tighten per-leg minimum clearance/bounds, keeping the 2D
    projection's original number of constraints. This finite grid is not a
    continuous collision proof; live checks and native acceptance still apply.
    """
    inverse=np.linalg.inv(body);q=dict(joints);clear=[];bounds=[]
    for foot in model.feet:
        position=np.asarray(targets[foot],dtype=float);future=np.asarray(future_targets[foot],dtype=float)
        if any(v.shape!=(3,) or not np.isfinite(v).all() for v in (position,future)):
            raise ValueError('finite reference geometry required')
        names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
        seed=tuple(joints[n] for n in names)
        nominal=ik_leg(model,foot,(inverse@np.r_[position,1.])[:3],seed)
        q.update(zip(names,nominal));angles=[nominal]
        low,high=envelope[foot]
        segment=(np.linspace(0.,1.,5) if foot==selected else (0.,))
        for u in segment:
            xy=position[:2]*(1.-u)+future[:2]*u
            for z in (low,(low+high)/2,high):
                angles.append(ik_leg(model,foot,(inverse@np.r_[xy,z,1.])[:3],seed))
        clear.append(min(thigh_trunk_clearance(model,foot,a)-.0001 for a in angles))
        for i,(part,name) in enumerate(zip(('hip','thigh','calf'),names)):
            lo=max(limits['gait_joint_bounds'][part][0],model.limits[name][0])
            hi=min(limits['gait_joint_bounds'][part][1],model.limits[name][1])
            bounds.extend((min(a[i]-lo for a in angles),min(hi-a[i] for a in angles)))
    return q,np.asarray(clear),np.asarray(bounds)
