"""Stance XYZ retargeting inside unchanged force, rate and geometry limits.

Only a prediction of the native position springs; never measured force or WBC.
Selected XY stays fixed. Each foot has one vector rate/offset cap, not per-axis
allowances. The ROS parent remains the sole reference and command owner.
"""
import math
import itertools
import time
from time import thread_time_ns
import numpy as np
from scipy.optimize import minimize
from .load_transition import SpatialLoadTransition
from .contact_equilibrium import leg_jacobian_local
from .leg_kinematics import fk_leg,_thigh_box_spec
from .reference_envelope import reference_constraints
from .carry_profile import _validate_limits

_L1=np.kron(np.eye(4),np.asarray(list(itertools.product((-1.,1.),repeat=3))))


class SpatialXYZTransition(SpatialLoadTransition):
    command_space='stance_xyz'

    def __init__(self,model,limits,*,terms_evaluator=None):
        _validate_limits(limits)
        super().__init__(model,terms_evaluator=terms_evaluator)
        self.limits=dict(limits)
        # Immutable URDF geometry only, never a measured-pose/distance cache.
        for f in model.feet:_thigh_box_spec(model.urdf,f)

    def step(self,*,foot,joints,body_pose,points,forces_world,target_forces,
             reference_xyz,origins,allowed_z,future_targets,dt,speed,min_force,
             command_joints=None,reference_pose=None):
        self.last_model=None;started=time.perf_counter_ns();cpu=thread_time_ns();feet=self.model.feet
        self.last_attempt=dict(scope='current_attempt_timing_not_force_measurement',stages={},
            preparation=self.preparation,command_space=self.command_space)
        def budget(stage):
            wall=time.perf_counter_ns()-started
            self.last_attempt['stages'][stage]=dict(wall_ns=wall,thread_cpu_ns=thread_time_ns()-cpu)
            if wall>10_000_000:
                self.last_attempt['rejected_at']=stage
                raise ValueError('transition optimization time budget')
        if (foot not in feet or any(set(v)!=set(feet) for v in
                (points,forces_world,reference_xyz,origins,allowed_z,future_targets))
                or not set(target_forces).issubset(feet)
                or not all(math.isfinite(v) for v in (dt,speed,min_force))
                or not 0.<dt<=.2 or not 0.<speed<=self.limits['unload_speed_mps']
                or min_force!=self.limits['min_contact_force_n']):
            raise ValueError('invalid spatial XYZ transition input')
        refs=np.asarray([reference_xyz[f] for f in feet],dtype=float)
        rest=np.asarray([origins[f] for f in feet],dtype=float)
        future=np.asarray([future_targets[f] for f in feet],dtype=float)
        force=np.asarray([forces_world[f] for f in feet],dtype=float)
        target=np.asarray([target_forces.get(f,[0.,0.,0.]) for f in feet],dtype=float)
        if (any(v.shape!=(4,3) or not np.isfinite(v).all() for v in (refs,rest,future,force,target))
                or np.any(force[:,2]<-1e-6)):
            raise ValueError('invalid spatial XYZ geometry/force')
        selected=feet.index(foot);unit=speed*dt;cap=self.limits['max_unload_height_m']
        if np.max(np.linalg.norm(refs-rest,axis=1))>cap+1e-10 or np.max(np.abs(refs[selected,:2]-rest[selected,:2]))>1e-12:
            raise ValueError('spatial XYZ original reference bounds')
        lower=np.full((4,3),-1.);upper=np.ones((4,3))
        lower[selected,:2]=upper[selected,:2]=0.
        for i,f in enumerate(feet):
            lo,hi=allowed_z[f]
            if not math.isfinite(lo) or not math.isfinite(hi) or lo>hi:
                raise ValueError('invalid spatial XYZ height bounds')
            lower[i,2]=max(-1.,(lo-refs[i,2])/unit)
            upper[i,2]=min(1.,(hi-refs[i,2])/unit)
            if i==selected:lower[i,2]=max(0.,lower[i,2])
        if np.any(lower>upper+1e-12):raise ValueError('spatial XYZ outside proven envelope')
        lower=lower.ravel();upper=np.maximum(lower,upper.ravel())
        budget('input_bounds')
        response=self.spatial_response(joints,body_pose,points);a=response*unit
        budget('spatial_response')
        flat=force.ravel();desired=(target-force).ravel()*dt;rows=[];bounds=[]
        command=joints if command_joints is None else command_joints
        command_pose=np.asarray(body_pose if reference_pose is None else reference_pose)
        torques={};entry_servo={}
        tangent=np.asarray(body_pose)[:3,0].copy();tangent[2]=0.;norm=np.linalg.norm(tangent)
        if norm<1e-9:raise ValueError('undefined flat contact tangent')
        tangent/=norm;second=np.cross([0.,0.,1.],tangent)
        for i,f in enumerate(feet):
            rows.append(-a[3*i+2]);bounds.append(force[i,2]-(0. if i==selected else min_force))
            for axis in (tangent,-tangent,second,-second):
                cone=axis.copy();cone[2]-=1./math.sqrt(2.)
                rows.append(cone@a[3*i:3*i+3]);bounds.append(-float(cone@force[i]))
            j=self._jacobians[f];tau=self._gravity[f]-j.T@force[i]
            mapping=-j.T@a[3*i:3*i+3]
            names=[f[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
            angles=np.asarray([command[n] for n in names]);local=np.asarray(fk_leg(self.model,f,angles))
            # Full world displacement -> local joint command derivative.
            dq=np.linalg.solve(leg_jacobian_local(self.model,f,angles,local),command_pose[:3,:3].T)*unit
            for k,n in enumerate(names):
                limit=self.model.limits[n][3];torques[n]=float(tau[k])
                effort=self.gains[n]*(command[n]-joints[n]);entry_servo[n]=float(effort)
                row=np.zeros(12);row[3*i:3*i+3]=self.gains[n]*dq[k]
                for sign in (1.,-1.):
                    rows.append(sign*mapping[k]);bounds.append(limit-sign*tau[k])
                    rows.append(sign*row);bounds.append(limit-sign*effort)
        offset=(refs-rest).ravel()/cap;ratio=unit/cap
        # Inscribed L1 balls: ||d||2 <= ||d||1. Fixed linear inequalities
        # conservatively enforce each vector cap without curved solver bounds.
        matrix=np.vstack((rows,_L1,ratio*_L1))
        rhs=np.r_[bounds,np.ones(32),np.ones(32)-_L1@offset]
        # A full spatial response has a six-dimensional rigid-motion nullspace.
        # Scale its quadratic and regularize references relative to curvature;
        # a dimensional 1e-10 penalty leaves a ~1e10 condition number here.
        scale=max(float(np.linalg.norm(a,2)**2),1e-12);regularizer=1e-3
        # Eliminate fixed coordinates, then whiten the positive-definite
        # quadratic. SLSQP now projects onto a polytope with identity Hessian;
        # this changes coordinates, not bounds, deadlines or primal objective.
        free=np.flatnonzero(upper-lower>1e-12);fixed=np.zeros(12)
        fixed[np.setdiff1d(np.arange(12),free)]=lower[np.setdiff1d(np.arange(12),free)]
        reduced=a[:,free];h=reduced.T@reduced/scale+regularizer*np.eye(len(free))
        upper_chol=np.linalg.cholesky(h).T
        transform=np.zeros((12,len(free)));transform[free]=np.linalg.solve(upper_chol,np.eye(len(free)))
        linear=(reduced.T@(desired-a@fixed))/scale
        optimum=np.linalg.solve(upper_chol.T,linear)
        transformed=np.vstack((matrix@transform,transform[free],-transform[free]))
        transformed_rhs=np.r_[rhs-matrix@fixed,upper[free],-lower[free]]
        def cost(y):return float((y-optimum)@(y-optimum))
        def jac(y):return 2.*(y-optimum)
        budget('constraints_ready')
        start=upper_chol@np.clip(np.zeros(len(free)),lower[free],upper[free])
        solution=minimize(cost,start,jac=jac,method='SLSQP',constraints=[dict(type='ineq',
                fun=lambda y:transformed_rhs-transformed@y,jac=lambda y:-transformed)],
            callback=lambda _:budget('solver_iteration'),options=dict(maxiter=32,ftol=1e-10))
        self.last_attempt['solver']=dict(status=int(solution.status),iterations=int(solution.nit),message=str(solution.message))
        budget('solver_finished')
        if not solution.success or solution.status!=0:
            raise ValueError('transition optimization failed: '+str(solution.message))
        value=fixed+transform@np.asarray(solution.x,dtype=float)
        if (value.shape!=(12,) or not np.isfinite(value).all() or np.max(matrix@value-rhs)>1e-7
                or np.any(value<lower-1e-9) or np.any(value>upper+1e-9)):
            raise ValueError('transition optimization XYZ residual')
        delta=(value*unit).reshape(4,3);proposed={f:v for f,v in zip(feet,refs+delta)}
        try:
            exact,clear,joint_bounds=reference_constraints(self.model,self.limits,joints,command_pose,
                proposed,allowed_z,selected=foot,future_targets=future_targets)
            if np.min(clear)<0. or np.min(joint_bounds)<0.:raise ValueError('clearance/bounds')
        except ValueError as error:
            raise ValueError('transition optimization future geometry: '+str(error)) from error
        servo={n:float(self.gains[n]*(exact[n]-joints[n])) for n in self.model.joint_names}
        if any(abs(v)>self.model.limits[n][3]+1e-6 for n,v in servo.items()):
            raise ValueError('transition optimization nonlinear servo residual')
        budget('exact_ik_validated')
        predicted=(flat+response@delta.ravel()).reshape(4,3);predicted_torque={}
        for i,f in enumerate(feet):
            tau=self._gravity[f]-self._jacobians[f].T@predicted[i]
            predicted_torque.update({f[:2]+'_'+p+'_joint':float(v) for p,v in zip(('hip','thigh','calf'),tau)})
        self.last_model=dict(scope='spatial_spring_prediction_not_measured_force_or_torque',
            command_space=self.command_space,predicted_forces_world={f:v.tolist() for f,v in zip(feet,predicted)},
            predicted_joint_torques=predicted_torque,current_joint_torque_estimates=torques,
            entry_position_error_effort=entry_servo,predicted_servo_command_efforts=servo,
            requested_delta_xyz={f:v.tolist() for f,v in zip(feet,delta)},future_geometry_validated=True,
            vector_bound_method='inscribed_l1',inequality_residual=float(max(0.,np.max(matrix@value-rhs))),
            optimization_iterations=int(solution.nit),compute_wall_ns=time.perf_counter_ns()-started)
        return {f:v.tolist() for f,v in zip(feet,delta)}
