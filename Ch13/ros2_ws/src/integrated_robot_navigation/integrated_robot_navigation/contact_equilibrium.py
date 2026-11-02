"""Bounded point-contact statics for the explicit load-transition profile.

Independent implementation inspired by actuation-aware feasible regions. This
is not a WBC or a claim that a position servo realizes a feasible force target.
All vectors are world-frame; joint torques include the modeled leg weight.
"""
import math
import time
import warnings
import numpy as np
from scipy.optimize import linprog, OptimizeWarning
from .leg_kinematics import _leg_spec, fk_leg
from .support import center_of_mass


def skew(v):
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def leg_jacobian_local(model,foot,angles,point):
    """Exact Rx/Ry/Ry Jacobian at a named body-frame contact point.

    Same revolute-axis cross products as the spatial construction, without
    generic NumPy axis dispatch or finite-difference FK calls in each tick.
    No measured position, force or derivative is cached.
    """
    fk_leg(model,foot,angles)
    hip,offset,upper,_,_=_leg_spec(model.urdf,foot)
    p=np.asarray(point,dtype=float)
    if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('finite local contact point required')
    roll,thigh,_=angles;c,s=math.cos(roll),math.sin(roll)
    shoulder=np.array([hip[0],hip[1]+offset*c,hip[2]+offset*s])
    knee=shoulder+np.array([-upper*math.sin(thigh),upper*math.cos(thigh)*s,
        -upper*math.cos(thigh)*c])
    a=p-hip;b=p-shoulder;d=p-knee
    return np.array([[0.,c*b[2]-s*b[1],c*d[2]-s*d[1]],
        [-a[2],s*b[0],s*d[0]],[a[1],-c*b[0],-c*d[0]]])


def leg_terms(model,joints,body_pose,points):
    """Contact Jacobians and gravity efforts, without force/servo feedback.

    Analytic revolute-axis Jacobians at the ACTUAL point of contact, not at
    the sphere center. Inertial points use the compiled, unchanged URDF.
    """
    pose=np.asarray(body_pose,dtype=float)
    if (pose.shape!=(4,4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3],[0.,0.,0.,1.],atol=1e-10)
            or not np.allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-8)
            or np.linalg.det(pose[:3,:3])<.999999):
        raise ValueError('rigid contact body pose required')
    if any(n not in joints or not math.isfinite(joints[n]) or not lo<=joints[n]<=hi
           for n,(lo,hi,_,_) in model.limits.items()):
        raise ValueError('finite bounded named joints required')
    inverse=np.linalg.inv(model.chains['base_link'].forward(joints))
    jacobians,gravity={},{}
    for foot in model.feet:
        hip,offset,upper,_,names=_leg_spec(model.urdf,foot)
        angles=np.array([joints[n] for n in names]);fk_leg(model,foot,angles)
        roll,thigh,_=angles;c,s=math.cos(roll),math.sin(roll)
        rx=np.array([[1.,0.,0.],[0.,c,-s],[0.,s,c]])
        local_thigh=np.asarray(hip)+rx@np.array([0.,offset,0.])
        local_calf=local_thigh+rx@np.array([-upper*math.sin(thigh),0.,-upper*math.cos(thigh)])
        origins=[pose[:3,3]+pose[:3,:3]@p for p in (hip,local_thigh,local_calf)]
        axes=[pose[:3,:3]@np.array([1.,0.,0.]),pose[:3,:3]@rx@np.array([0.,1.,0.])]
        axes.append(axes[1])
        point=np.asarray(points[foot],dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all():
            raise ValueError('finite named world contact points required')
        jacobians[foot]=pose[:3,:3]@leg_jacobian_local(model,foot,angles,
            pose[:3,:3].T@(point-pose[:3,3]))
        effort=np.zeros(3)
        for link,(mass,local) in model.masses.items():
            if not link.startswith(foot[:2]+'_'):continue
            chain=model.chains[link]
            active={spec[0] for spec in chain.compiled if spec[1]!='fixed'}
            world=(pose@inverse@chain.forward(joints)@np.r_[local,1.])[:3]
            for i,name in enumerate(names):
                if name in active:
                    # For vertical gravity cross(r,[0,0,mg])=(mg*r_y,-mg*r_x,0).
                    r=world-origins[i];axis=axes[i]
                    effort[i]+=9.81*mass*(axis[0]*r[1]-axis[1]*r[0])
        gravity[foot]=effort
    return jacobians,gravity


def static_support(model,joints,body_pose,points,active_feet,*,com=None,
                   friction=1.,min_force=2.,effort_limits=None,terms_evaluator=None,actuation_evaluator=None):
    """Minimize maximum modeled actuator utilization, retaining full statics.

    The LP is allowed to report utilization >1: its negative margin guides
    the candidate search, but cannot authorize that candidate. No successful
    solver status is trusted before independent primal residual checks.
    """
    started=time.perf_counter_ns();active=tuple(active_feet)
    if (len(active) not in (3,4) or len(set(active))!=len(active)
            or not set(active).issubset(model.feet) or set(points)!=set(model.feet)
            or not math.isfinite(friction) or friction<=0.
            or not math.isfinite(min_force) or min_force<0.):
        raise ValueError('finite three/four-contact equilibrium input required')
    if terms_evaluator is None:
        jacobians,gravity=leg_terms(model,joints,body_pose,points)
    else:
        jacobians,gravity=terms_evaluator(model,joints,body_pose,points)
        if (not isinstance(jacobians,dict) or not isinstance(gravity,dict)
                or set(jacobians)!=set(model.feet) or set(gravity)!=set(model.feet)
                or any(np.shape(jacobians[f])!=(3,3) or np.shape(gravity[f])!=(3,)
                    or not np.isfinite(jacobians[f]).all() or not np.isfinite(gravity[f]).all()
                    for f in model.feet)):
            raise ValueError('invalid current support contact terms')
    limits={n:model.limits[n][3] for n in model.joint_names} if effort_limits is None else dict(effort_limits)
    if (set(limits)!=set(model.joint_names)
            or any(not math.isfinite(v) or v<=0. for v in limits.values())):
        raise ValueError('positive named actuator limits required')
    center=np.asarray(center_of_mass(model,joints,body_pose) if com is None else com,dtype=float)
    if center.shape!=(3,) or not np.isfinite(center).all():raise ValueError('finite CoM required')
    count=3*len(active);eq=np.zeros((6,count+1))
    for i,foot in enumerate(active):
        eq[:3,3*i:3*i+3]=np.eye(3)
        eq[3:,3*i:3*i+3]=skew(np.asarray(points[foot])-center)
    target=np.array([0.,0.,9.81*sum(m for m,_ in model.masses.values()),0.,0.,0.])
    rows=[];bounds=[]
    # Inscribed friction square, aligned with body yaw on the verified flat
    # floor. Its corners remain within the physical circular Coulomb cone.
    tangent=np.asarray(body_pose)[:3,0].copy();tangent[2]=0.
    norm=np.linalg.norm(tangent)
    if norm<1e-9:raise ValueError('undefined flat contact tangent')
    tangent/=norm;second=np.cross([0.,0.,1.],tangent)
    for i,foot in enumerate(active):
        for axis in (tangent,-tangent,second,-second):
            row=np.zeros(count+1);row[3*i:3*i+3]=axis
            row[3*i+2]-=friction/math.sqrt(2.)
            rows.append(row);bounds.append(0.)
    for foot in model.feet:
        for j,part in enumerate(('hip','thigh','calf')):
            name=foot[:2]+'_'+part+'_joint'
            for sign in (1.,-1.):
                row=np.zeros(count+1);row[-1]=-limits[name]
                if foot in active:
                    i=active.index(foot);row[3*i:3*i+3]=-sign*jacobians[foot][:,j]
                rows.append(row);bounds.append(-sign*gravity[foot][j])
    actuation=None
    if actuation_evaluator is not None:
        actuation=actuation_evaluator(model,joints,body_pose,points)
        names=tuple(actuation['names']);command_bias=np.asarray(actuation['gravity'],dtype=float)
        command_map=np.asarray(actuation['force_to_command'],dtype=float);command_caps=np.asarray(actuation['effort'],dtype=float).copy()
        if (len(names)!=len(model.limits) or set(names)!=set(model.limits) or tuple(actuation['feet'])!=tuple(model.feet)
                or command_bias.shape!=(len(names),) or command_caps.shape!=(len(names),) or command_map.shape!=(len(names),12)
                or not all(np.isfinite(v).all() for v in (command_bias,command_map,command_caps))
                or np.min(command_caps)<=0. or any(command_caps[i]>model.limits[name][3]+1e-12 for i,name in enumerate(names))
                or actuation.get('model')!='gazebo_discrete_equilibrium_v1'):
            raise ValueError('invalid original20-axis actuator command model')
        for i,name in enumerate(names):
            if name in limits:command_caps[i]=min(command_caps[i],limits[name])
        columns=[3*model.feet.index(foot)+axis for foot in active for axis in range(3)]
        for i,name in enumerate(names):
            for sign in (1.,-1.):
                row=np.zeros(count+1);row[:count]=sign*command_map[i,columns];row[-1]=-command_caps[i]
                rows.append(row);bounds.append(-sign*command_bias[i])
    inequality=np.asarray(rows);rhs=np.asarray(bounds)
    objective=np.zeros(count+1);objective[-1]=1.
    variable_bounds=[(None,None) if i%3!=2 else (min_force,None) for i in range(count)]+[(0.,None)]
    # scipy documents forwarding unrecognized options to HiGHS; this exact
    # option bounds its worker count. Other warnings/errors remain visible.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message=r"Unrecognized options detected: .*threads",category=OptimizeWarning)
        result=linprog(objective,A_ub=inequality,b_ub=rhs,A_eq=eq,b_eq=target,
            bounds=variable_bounds,method='highs-ds',options=dict(threads=1,time_limit=.01,
            dual_feasibility_tolerance=1e-8,primal_feasibility_tolerance=1e-8))
    if not result.success or result.status!=0:
        raise ValueError('equilibrium optimization failed: '+str(result.message))
    value=np.asarray(result.x,dtype=float)
    if value.shape!=(count+1,) or not np.isfinite(value).all():
        raise ValueError('equilibrium residual: invalid solution')
    eq_error=float(np.max(np.abs(eq@value-target)))
    ineq_error=float(max(0.,np.max(inequality@value-rhs),-value[-1],
        max(min_force-value[i] for i in range(2,count,3))))
    if eq_error>1e-6 or ineq_error>1e-7:
        raise ValueError('equilibrium residual exceeds tolerance')
    forces={f:value[3*i:3*i+3].tolist() for i,f in enumerate(active)}
    torques={}
    for foot in model.feet:
        tau=gravity[foot]-jacobians[foot].T@np.asarray(forces.get(foot,[0.,0.,0.]))
        torques.update({foot[:2]+'_'+part+'_joint':float(t) for part,t in zip(('hip','thigh','calf'),tau)})
    usage=max(abs(torques[n])/limits[n] for n in model.joint_names)
    actuation_proof={}
    if actuation is not None:
        physical_usage=usage
        flat=np.asarray([forces.get(foot,[0.,0.,0.]) for foot in model.feet]).ravel()
        commands=command_bias+command_map@flat
        usage=max(usage,float(np.max(np.abs(commands)/command_caps)))
        actuation_proof=dict(actuation_model=actuation['model'],actuator_command_efforts=dict(zip(names,commands.tolist())),
            physical_torque_utilization=float(physical_usage),actuation_library_sha256=actuation['library_sha256'])
        forces={foot:forces.get(foot,[0.,0.,0.]) for foot in model.feet}
    return dict(scope='quasistatic_point_contact_prediction_not_measured_force',
        feasible=bool(usage<=1.+1e-8),torque_utilization=float(usage),margin=float(1.-usage),
        forces_world=forces,joint_torques=torques,com_world=center.tolist(),
        equilibrium_residual_n=eq_error,inequality_residual=ineq_error,
        compute_wall_ns=time.perf_counter_ns()-started,**actuation_proof)
