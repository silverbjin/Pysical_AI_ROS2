"""Spatial spring response and bounded position commands, not SEIKO itself.

The six-axis floating body is eliminated from the linear contact response.
The optimizer owns all four height increments, including the selected foot;
the caller must not append another independent unload ramp afterwards.
"""
import math
import time
from time import thread_time_ns
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import minimize
from .contact_equilibrium import leg_terms,leg_jacobian_local,skew
from .leg_kinematics import fk_leg,ik_leg


class SpatialLoadTransition:
    def __init__(self,model,*,terms_evaluator=None):
        self.model=model;tree=ET.fromstring(model.urdf);self.gains={};self.last_model=None
        self.preparation=None;self.last_attempt=None
        self._terms_evaluator=leg_terms if terms_evaluator is None else terms_evaluator
        for name in model.joint_names:
            values=tree.findall(f"ros2_control/joint[@name='{name}']/param[@name='ch13_kp']")
            try:gain=float(values[0].text) if len(values)==1 else float('nan')
            except (ValueError,TypeError):gain=float('nan')
            if not math.isfinite(gain) or gain<=0.:raise ValueError('verified native stiffness required')
            self.gains[name]=gain

    def prepare(self):
        """Load and verify numeric solver internals before motor activation.

        This bounded four-variable arithmetic problem has no sensor input,
        reference output or simulated contact. It cannot authorize motion.
        """
        if self.preparation is not None:return dict(self.preparation)
        started=time.perf_counter_ns();cpu=thread_time_ns();target=np.array([.1,-.1,.2,-.2])
        result=minimize(lambda x:float((x-target)@(x-target)),np.zeros(4),
            jac=lambda x:2.*(x-target),method='SLSQP',bounds=[(-1.,1.)]*4,
            constraints=[dict(type='ineq',fun=lambda x:1.-x,jac=lambda x:-np.eye(4))],
            options=dict(maxiter=8,ftol=1e-12))
        if (not result.success or result.status!=0 or np.shape(result.x)!=(4,)
                or not np.isfinite(result.x).all() or np.max(np.abs(result.x-target))>1e-8):
            raise ValueError('solver preparation failed: '+str(result.message))
        self.preparation=dict(scope='numeric_solver_initialization_not_contact_admission',
            solver_verified=True,calls=1,wall_ns=time.perf_counter_ns()-started,
            thread_cpu_ns=thread_time_ns()-cpu)
        return dict(self.preparation)

    def response(self,joints,body_pose,points):
        return self.spatial_response(joints,body_pose,points)[:,[2,5,8,11]]

    def spatial_response(self,joints,body_pose,points):
        jacobians,gravity=self._terms_evaluator(self.model,joints,body_pose,points)
        stiffness=np.zeros((12,12));body=np.zeros((12,6))
        origin=np.asarray(body_pose)[:3,3]
        for i,foot in enumerate(self.model.feet):
            names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
            j=jacobians[foot]
            compliance=(j/np.array([self.gains[n] for n in names]))@j.T
            if np.linalg.eigvalsh(compliance)[0]<1e-14:
                raise ValueError('singular spatial contact compliance')
            stiffness[3*i:3*i+3,3*i:3*i+3]=np.linalg.inv(compliance)
            body[3*i:3*i+3]=np.column_stack((np.eye(3),-skew(np.asarray(points[foot])-origin)))
        product=stiffness@body;system=body.T@product
        if not np.isfinite(system).all() or np.linalg.cond(system)>1e12:
            raise ValueError('singular floating-body contact response')
        projector=stiffness-product@np.linalg.solve(system,product.T)
        projector=(projector+projector.T)/2.
        self._jacobians,self._gravity=jacobians,gravity
        return -projector

    def step(self,*,foot,joints,body_pose,points,forces_world,target_forces,
             reference_z,origins,allowed_z,dt,speed,min_force,
             command_joints=None,reference_pose=None):
        self.last_model=None;started=time.perf_counter_ns();cpu=thread_time_ns();feet=self.model.feet
        self.last_attempt=dict(scope='current_attempt_timing_not_force_measurement',stages={},preparation=self.preparation)
        def budget(checkpoint):
            wall=time.perf_counter_ns()-started
            self.last_attempt['stages'][checkpoint]=dict(wall_ns=wall,thread_cpu_ns=thread_time_ns()-cpu)
            if wall>10_000_000:
                self.last_attempt['rejected_at']=checkpoint
                raise ValueError('transition optimization time budget')
        if (foot not in feet or set(points)!=set(feet) or set(forces_world)!=set(feet)
                or set(reference_z)!=set(feet) or set(origins)!=set(feet) or set(allowed_z)!=set(feet)
                or not set(target_forces).issubset(feet)
                or not all(math.isfinite(v) for v in (dt,speed,min_force))
                or not 0.<dt<=.2 or speed<=0. or min_force<=0.):
            raise ValueError('invalid spatial transition input')
        force=np.asarray([forces_world[f] for f in feet],dtype=float)
        target=np.asarray([target_forces.get(f,[0.,0.,0.]) for f in feet],dtype=float)
        if (force.shape!=(4,3) or target.shape!=(4,3) or not np.isfinite(force).all()
                or not np.isfinite(target).all() or np.any(force[:,2]<-1e-6)):
            raise ValueError('invalid signed world force input')
        # This is the allowed position transition rate, never a force override.
        unit=speed*dt;lower=[];upper=[]
        for f in feet:
            lo,hi=allowed_z[f];z=reference_z[f];rest=origins[f]
            if not all(math.isfinite(v) for v in (lo,hi,z,rest)) or lo>hi:
                raise ValueError('invalid spatial reference bounds')
            lo=max(lo,rest-.01);hi=min(hi,rest+.01)
            low=max(-unit,lo-z);high=min(unit,hi-z)
            if f==foot:low=max(0.,low)
            if low>high+1e-12:raise ValueError('spatial reference outside proven envelope')
            lower.append(low/unit);upper.append(max(low,high)/unit)
        budget('input_bounds')
        response=self.response(joints,body_pose,points)
        budget('spatial_response')
        a=response*unit;flat=force.ravel();desired=(target-force).ravel()*dt
        rows=[];bounds=[];torques={}
        command=joints if command_joints is None else command_joints
        command_pose=np.asarray(body_pose if reference_pose is None else reference_pose)
        command_local={};entry_servo={}
        tangent=np.asarray(body_pose)[:3,0].copy();tangent[2]=0.;norm=np.linalg.norm(tangent)
        if norm<1e-9:raise ValueError('undefined flat contact tangent')
        tangent/=norm;second=np.cross([0.,0.,1.],tangent)
        for i,f in enumerate(feet):
            minimum=0. if f==foot else min_force
            rows.append(-a[3*i+2]);bounds.append(force[i,2]-minimum)
            for axis in (tangent,-tangent,second,-second):
                cone=axis.copy();cone[2]-=1./math.sqrt(2.)
                rows.append(cone@a[3*i:3*i+3]);bounds.append(-float(cone@force[i]))
            j=self._jacobians[f];tau=self._gravity[f]-j.T@force[i]
            mapping=-j.T@a[3*i:3*i+3]
            names=[f[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
            angles=np.asarray([command[n] for n in names]);local=np.asarray(fk_leg(self.model,f,angles))
            derivative=leg_jacobian_local(self.model,f,angles,local)
            dz=np.linalg.solve(derivative,command_pose[:3,:3].T@np.array([0.,0.,1.]))
            command_local[f]=local
            for k,part in enumerate(('hip','thigh','calf')):
                name=f[:2]+'_'+part+'_joint';limit=self.model.limits[name][3]
                torques[name]=float(tau[k])
                for sign in (1.,-1.):
                    rows.append(sign*mapping[k]);bounds.append(limit-sign*tau[k])
                # Also constrain the native position spring's actual command
                # error model. A static contact torque is NOT that command.
                effort=self.gains[name]*(command[name]-joints[name]);entry_servo[name]=float(effort)
                row=np.zeros(4);row[i]=self.gains[name]*dz[k]*unit
                for sign in (1.,-1.):
                    rows.append(sign*row);bounds.append(limit-sign*effort)
        matrix=np.asarray(rows);rhs=np.asarray(bounds);regularizer=1e-10
        budget('constraints_ready')
        def cost(x):
            error=a@x-desired
            return float(error@error+regularizer*(x@x))
        def jac(x):return 2.*(a.T@(a@x-desired)+regularizer*x)
        solution=minimize(cost,np.clip(np.zeros(4),lower,upper),jac=jac,method='SLSQP',
            bounds=list(zip(lower,upper)),constraints=[dict(type='ineq',
            fun=lambda x:rhs-matrix@x,jac=lambda x:-matrix)],
            callback=lambda _:budget('solver_iteration'),options=dict(maxiter=32,ftol=1e-10))
        budget('solver_finished')
        if not solution.success or solution.status!=0:
            raise ValueError('transition optimization failed: '+str(solution.message))
        value=np.asarray(solution.x,dtype=float)
        if (value.shape!=(4,) or not np.isfinite(value).all()
                or np.max(matrix@value-rhs)>1e-7
                or np.any(value<np.asarray(lower)-1e-9) or np.any(value>np.asarray(upper)+1e-9)):
            raise ValueError('transition optimization residual')
        delta=value*unit;predicted=(flat+response@delta).reshape(4,3)
        predicted_torque={}
        servo_torque={}
        for i,f in enumerate(feet):
            tau=self._gravity[f]-self._jacobians[f].T@predicted[i]
            predicted_torque.update({f[:2]+'_'+p+'_joint':float(v) for p,v in zip(('hip','thigh','calf'),tau)})
            names=[f[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
            point=command_local[f]+command_pose[:3,:3].T@np.array([0.,0.,delta[i]])
            exact=ik_leg(self.model,f,point,tuple(command[n] for n in names))
            for n,q in zip(names,exact):
                effort=self.gains[n]*(q-joints[n]);servo_torque[n]=float(effort)
                if abs(effort)>self.model.limits[n][3]+1e-6:
                    raise ValueError('transition optimization nonlinear servo residual')
        budget('exact_ik_validated')
        self.last_model=dict(scope='spatial_spring_prediction_not_measured_force_or_torque',
            predicted_forces_world={f:v.tolist() for f,v in zip(feet,predicted)},
            predicted_joint_torques=predicted_torque,requested_delta_z=dict(zip(feet,delta.tolist())),
            current_joint_torque_estimates=torques,
            entry_position_error_effort=entry_servo,predicted_servo_command_efforts=servo_torque,
            inequality_residual=float(max(0.,np.max(matrix@value-rhs))),
            optimization_iterations=int(solution.nit),compute_wall_ns=time.perf_counter_ns()-started)
        return {f:float(d) for f,d in zip(feet,delta)}
