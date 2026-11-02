"""Bounded vertical stance admittance for the explicit Gazebo G2 experiment.

This is a flat, quasi-static spring approximation, not SEIKO/WBC. Four normal
forces have one redundant direction after total force and roll/pitch moments
are fixed. Position feedback alone does not choose that direction. No force,
root pose, motor gain, or measured contact is written here.
"""
import math
import xml.etree.ElementTree as ET
import numpy as np
from .leg_kinematics import fk_leg


def balanced_support_weight(initial,direction,predict,support,margin,horizon_budget):
    """Yield at each IK/mass candidate; prefer balanced *predicted* loads.

    The caller already proved the initial candidate's path. Keep it if the
    improved endpoint's path/future-foot IK fails. This is a bounded geometry
    objective, not a force command, measured stability or saturation proof.
    """
    points=np.asarray(support,dtype=float)
    if points.shape!=(3,3) or not np.isfinite(points).all() or not 0<=initial<=1:
        raise ValueError('finite three-foot support balance input required')
    matrix=np.vstack((points[:,:2].T,np.ones(3)))
    if abs(np.linalg.det(matrix))<1e-9:raise ValueError('degenerate support load triangle')
    from .support import support_margin
    best=initial;best_score=float('inf');best_loads=None;rows=[]
    for weight in np.linspace(initial,1.,9):
        row=dict(weight=float(weight))
        try:
            point=predict(float(weight),direction)
            actual_margin=support_margin(point,support)
            if actual_margin<margin:raise ValueError('predicted support margin')
            loads=np.linalg.solve(matrix,np.r_[point[:2],1.])
            score=float(loads.max())
            if not np.isfinite(loads).all() or np.any(loads<0):raise ValueError('invalid predicted load fraction')
            row.update(peak_fraction=score,fractions=loads.tolist(),margin_m=actual_margin)
            if score<best_score:
                best=float(weight);best_score=score;best_loads=loads.tolist()
        except ValueError as error:row['rejected']=str(error)
        rows.append(row)
        yield
    if best_loads is None:
        raise ValueError('no valid support load candidate')
    rejection=None
    if best!=initial:
        for progress in (.25,.5,.75):
            try:predict(best,direction,progress=progress)
            except ValueError as error:rejection=str(error)
            yield
            if rejection:break
        if rejection is None:
            try:predict(best,direction,horizon_budget=horizon_budget)
            except ValueError as error:rejection=str(error)
            yield
    selected=initial if rejection else best
    return selected,dict(scope='quasistatic_vertical_prediction_not_measured_force',
        initial_weight=initial,selected_weight=selected,candidates=rows,
        proposed_peak_fraction=best_score if best_loads is not None else None,
        proposed_fractions=best_loads,path_rejection=rejection)


class StanceLoadTransfer:
    def __init__(self,model):
        self.model=model;tree=ET.fromstring(model.urdf);self.gains={}
        self.last_linear_model=None
        for name in model.joint_names:
            values=tree.findall(f"ros2_control/joint[@name='{name}']/param[@name='ch13_kp']")
            try:gain=float(values[0].text) if len(values)==1 else float('nan')
            except (TypeError,ValueError):gain=float('nan')
            if not math.isfinite(gain) or gain<=0:raise ValueError('verified native stiffness required')
            self.gains[name]=gain

    def vertical_compliance(self,foot,joints,rotation):
        names=[foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf')]
        angles=np.asarray([joints[n] for n in names]);value=0.
        for index,name in enumerate(names):
            delta=np.zeros(3);delta[index]=1e-6
            jac=float(rotation[2]@(np.asarray(fk_leg(self.model,foot,angles+delta))
                                  -fk_leg(self.model,foot,angles-delta)))/(2e-6)
            value+=jac*jac/self.gains[name]
        if not math.isfinite(value) or value<=1e-12:raise ValueError('singular vertical compliance')
        return value

    def correction(self,*,foot,joints,rotation,points,forces,dt,speed,min_force):
        self.last_linear_model=None
        rotation=np.asarray(rotation,dtype=float);forces=np.asarray(forces,dtype=float)
        positions=np.asarray([points[f] for f in self.model.feet],dtype=float)
        if (foot not in self.model.feet or positions.shape!=(4,3) or not np.isfinite(positions).all()
                or forces.shape!=(4,) or not np.isfinite(forces).all() or np.any(forces<0)
                or rotation.shape!=(3,3) or not np.isfinite(rotation).all()
                or not np.allclose(rotation@rotation.T,np.eye(3),atol=1e-7)
                or np.linalg.det(rotation)<.999999
                or not all(math.isfinite(v) for v in (dt,speed,min_force))
                or not 0<=dt<=.2 or speed<=0 or min_force<=0):
            raise ValueError('invalid stance load transfer input')
        selected=self.model.feet.index(foot)
        result={f:0. for f in self.model.feet if f!=foot}
        # A low support sample starts release confirmation; it does not end
        # regulation. Only the caller's confirmed SHIFT->SWING handoff does.
        if dt==0 or forces[selected]==0.:return result
        # H.T*f = [sum(Fz), roll moment, pitch moment]. Nullspace feedback
        # changes redundant internal load without requesting a net body wrench.
        h=np.column_stack((np.ones(4),positions[:,1],-positions[:,0]))
        _,singular,vh=np.linalg.svd(h.T)
        null=vh[-1]
        if singular[-1]<1e-6 or abs(null[selected])<1e-6:
            raise ValueError('degenerate contact load geometry')
        desired=-forces[selected]*null/null[selected]
        fraction=1.
        for i,f in enumerate(self.model.feet):
            if f!=foot and desired[i]<0:
                fraction=min(fraction,max(0.,(forces[i]-min_force)/-desired[i]))
        compliance=np.array([self.vertical_compliance(f,joints,rotation) for f in self.model.feet])
        weights=compliance*null*null
        # Free-body compliance P = n*n.T/(n.T*C*n). Holding the selected
        # reference removes its contribution; independent spring corrections
        # otherwise deliver only mu of the intended force-error step. Invert
        # this measured-geometry coupling before applying the original cap.
        coupling=float((weights.sum()-weights[selected])/weights.sum())
        if not math.isfinite(coupling) or coupling<=1e-9:
            raise ValueError('singular held-foot load response')
        # One-second linear force-error step (before the existing rate cap).
        # The selected foot retains its original bounded unload owner.
        for i,f in enumerate(self.model.feet):
            if f!=foot:
                result[f]=-compliance[i]*desired[i]*fraction*dt/coupling
        peak=max(abs(v) for v in result.values());scale=min(1.,speed*dt/peak) if peak else 1.
        self.last_linear_model=dict(scope='flat_free_body_prediction_not_measured_force',
            coupling_fraction=coupling,inverse_coupling=1/coupling,
            compliance_m_per_n=compliance.tolist(),command_rate_scale=scale,
            predicted_selected_force_step_n=float(desired[selected]*fraction*dt*scale))
        return {f:float(v*scale) for f,v in result.items()}
