"""Same bounded spatial QP in one native call; parent still owns commands."""
import ctypes,hashlib,json,math,time,weakref
from pathlib import Path
from time import thread_time_ns
import numpy as np
from ament_index_python.packages import get_package_prefix
from .load_xyz import SpatialXYZTransition
from .leg_kinematics import _leg_spec

UPSTREAM_COMMIT='11602ec9f87a62a97ba8318ebd81da6646f3c631'


def optimizer_library_path():
    return Path(get_package_prefix('integrated_robot_navigation_sensors'))/'lib/libnavigation_xyz_optimizer.so'


class _NativeXYZPlan:
    def __init__(self,model,limits,gains,force_objective):
        self.names=tuple(n for f in model.feet for n in _leg_spec(model.urdf,f)[4])
        legs=[]
        for f in model.feet:
            hip,offset,upper,lower,_=_leg_spec(model.urdf,f)
            legs.append(dict(hip=list(hip),offset=offset,upper=upper,lower=lower))
        data=dict(gains=[gains[n] for n in self.names],effort=[model.limits[n][3] for n in self.names],
            physical=[v for n in self.names for v in model.limits[n][:2]],legs=legs,
            cap=limits['max_unload_height_m'],speed=limits['unload_speed_mps'],min_force=limits['min_contact_force_n'],
            force_objective=force_objective)
        payload=json.dumps(data,allow_nan=False).encode();path=optimizer_library_path();lib=ctypes.CDLL(str(path))
        upstream=path.parent.parent/'share/integrated_robot_navigation_sensors/third_party/qpmad/UPSTREAM.json'
        manifest=json.loads(upstream.read_text())
        if manifest['commit']!=UPSTREAM_COMMIT:raise ValueError('native XYZ upstream identity')
        lib.ch13_xyz_abi_version.restype=ctypes.c_int
        if lib.ch13_xyz_abi_version()!=1:raise ValueError('native XYZ ABI mismatch')
        lib.ch13_xyz_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t];lib.ch13_xyz_create.restype=ctypes.c_void_p
        lib.ch13_xyz_destroy.argtypes=[ctypes.c_void_p];lib.ch13_xyz_destroy.restype=None
        lib.ch13_xyz_prepare.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t];lib.ch13_xyz_prepare.restype=ctypes.c_int
        pointer=ctypes.POINTER(ctypes.c_double)
        lib.ch13_xyz_evaluate.argtypes=[ctypes.c_void_p,pointer,ctypes.c_size_t,ctypes.c_int,pointer,ctypes.c_size_t,pointer,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_size_t]
        lib.ch13_xyz_evaluate.restype=ctypes.c_int
        error=ctypes.create_string_buffer(1024);handle=lib.ch13_xyz_create(payload,error,len(error))
        if not handle:raise ValueError('native XYZ plan: '+error.value.decode(errors='replace'))
        self._library=lib;self._handle=handle;self._finalize=weakref.finalize(self,lib.ch13_xyz_destroy,handle)
        self.last_timings=np.zeros(8)
        self.provenance=dict(scope='native_spatial_QP_arithmetic_no_command_or_measured_cache',abi=1,
            library=str(path),library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            geometry_sha256=hashlib.sha256(payload).hexdigest(),upstream_commit=UPSTREAM_COMMIT,
            upstream_manifest_sha256=hashlib.sha256(upstream.read_bytes()).hexdigest(),max_iterations=32,
            force_objective=force_objective,model_sha256=model.model_sha256)

    def prepare(self):
        if not self._finalize.alive:raise RuntimeError('native XYZ optimizer closed')
        error=ctypes.create_string_buffer(1024)
        if self._library.ch13_xyz_prepare(self._handle,error,len(error)):
            raise ValueError('native XYZ preparation: '+error.value.decode(errors='replace'))

    def solve(self,values,selected):
        if not self._finalize.alive:raise RuntimeError('native XYZ optimizer closed')
        values=np.ascontiguousarray(values,dtype=np.float64)
        if values.shape!=(175,):raise ValueError('transition optimization native XYZ dimensions')
        pointer=ctypes.POINTER(ctypes.c_double);output=np.zeros(208);self.last_timings=np.zeros(8)
        error=ctypes.create_string_buffer(1024)
        code=self._library.ch13_xyz_evaluate(self._handle,values.ctypes.data_as(pointer),len(values),selected,
            output.ctypes.data_as(pointer),len(output),self.last_timings.ctypes.data_as(pointer),len(self.last_timings),error,len(error))
        if code:raise ValueError('transition optimization native XYZ: '+error.value.decode(errors='replace')+' code='+str(code))
        if not np.isfinite(output).all():raise ValueError('transition optimization nonfinite native result')
        return output

    def close(self):self._finalize()


class NativeXYZTransition(SpatialXYZTransition):
    def __init__(self,model,limits,*,terms_evaluator=None,force_objective='rate_1_per_s'):
        if force_objective not in ('rate_1_per_s','bounded_terminal_force'):
            raise ValueError('unknown spatial force objective')
        self.force_objective=force_objective
        super().__init__(model,limits,terms_evaluator=terms_evaluator)
        try:self._optimizer=_NativeXYZPlan(model,limits,self.gains,force_objective)
        except BaseException:
            self.geometry.close();raise

    def prepare(self):
        if not self._optimizer._finalize.alive:raise RuntimeError('native XYZ optimizer closed')
        if self.preparation is not None:return dict(self.preparation)
        start=time.perf_counter_ns();cpu=thread_time_ns();self._optimizer.prepare()
        self.preparation=dict(scope='numeric_solver_initialization_not_contact_admission',solver_verified=True,calls=1,
            backend='qpmad_1_5_1_native',force_objective=self.force_objective,
            wall_ns=time.perf_counter_ns()-start,thread_cpu_ns=thread_time_ns()-cpu)
        return dict(self.preparation)

    def close(self):
        self._optimizer.close();self.geometry.close()

    def step(self,*,foot,joints,body_pose,points,forces_world,target_forces,
             reference_xyz,origins,allowed_z,future_targets,dt,speed,min_force,command_joints=None,reference_pose=None):
        if not self._optimizer._finalize.alive:raise RuntimeError('native XYZ optimizer closed')
        self.last_model=None;self.last_response=None;start=time.perf_counter_ns();cpu=thread_time_ns();feet=self.model.feet
        self.last_attempt=dict(scope='current_attempt_timing_not_force_measurement',stages={},preparation=self.preparation,
            command_space=self.command_space,optimization_backend='qpmad_1_5_1_native',force_objective=self.force_objective)
        def budget(stage):
            wall=time.perf_counter_ns()-start
            self.last_attempt['stages'][stage]=dict(wall_ns=wall,thread_cpu_ns=thread_time_ns()-cpu)
            if wall>10_000_000:
                self.last_attempt['rejected_at']=stage;raise ValueError('transition optimization time budget')
        if (foot not in feet or any(set(v)!=set(feet) for v in (points,forces_world,reference_xyz,origins,allowed_z,future_targets))
                or not set(target_forces).issubset(feet) or not all(math.isfinite(v) for v in (dt,speed,min_force))
                or not 0.<dt<=.2 or not 0.<speed<=self.limits['unload_speed_mps'] or min_force!=self.limits['min_contact_force_n']):
            raise ValueError('invalid spatial XYZ transition input')
        refs=np.asarray([reference_xyz[f] for f in feet],dtype=float)
        rest=np.asarray([origins[f] for f in feet],dtype=float);future=np.asarray([future_targets[f] for f in feet],dtype=float)
        force=np.asarray([forces_world[f] for f in feet],dtype=float)
        target=np.asarray([target_forces.get(f,[0.,0.,0.]) for f in feet],dtype=float)
        envelope=np.asarray([allowed_z[f] for f in feet],dtype=float)
        if (any(v.shape!=(4,3) or not np.isfinite(v).all() for v in (refs,rest,future,force,target))
                or envelope.shape!=(4,2) or not np.isfinite(envelope).all()):
            raise ValueError('invalid spatial XYZ geometry/force')
        budget('input_bounds')
        jacobians,gravity=self._terms_evaluator(self.model,joints,body_pose,points)
        command=joints if command_joints is None else command_joints
        pose=np.asarray(body_pose,dtype=float);reference=np.asarray(body_pose if reference_pose is None else reference_pose,dtype=float)
        if pose.shape!=(4,4) or reference.shape!=(4,4):raise ValueError('transition optimization XYZ pose dimensions')
        values=np.r_[[joints[n] for n in self._optimizer.names],[command[n] for n in self._optimizer.names],
            pose.ravel(),reference.ravel(),np.asarray([points[f] for f in feet]).ravel(),force.ravel(),target.ravel(),refs.ravel(),rest.ravel(),envelope.ravel(),
            np.asarray([jacobians[f] for f in feet]).ravel(),np.asarray([gravity[f] for f in feet]).ravel(),dt,speed,min_force]
        budget('contact_terms');offset_wall=time.perf_counter_ns()-start;offset_cpu=thread_time_ns()-cpu
        def native_trace():
            for i,name in enumerate(('spatial_response','constraints_ready','solver_finished','native_result_validated')):
                w,c=self._optimizer.last_timings[2*i:2*i+2]
                if w>0:self.last_attempt['stages'][name]=dict(wall_ns=int(offset_wall+w),thread_cpu_ns=int(offset_cpu+c))
        try:result=self._optimizer.solve(values,feet.index(foot))
        except ValueError as error:
            native_trace();self.last_attempt['native_error']=str(error);budget('native_qp_rejected');raise
        native_trace();budget('native_qp_returned')
        delta=result[:12].reshape(4,3);proposed={f:p for f,p in zip(feet,refs+delta)}
        try:
            exact,clear,bounds=self.geometry.evaluate(joints=joints,body=reference,targets=proposed,envelope=allowed_z,selected=foot,future_targets=future_targets)
            if np.min(clear)<0. or np.min(bounds)<0.:raise ValueError('clearance/bounds')
        except ValueError as error:raise ValueError('transition optimization future geometry: '+str(error)) from error
        servo={n:float(self.gains[n]*(exact[n]-joints[n])) for n in self.model.joint_names}
        if any(abs(v)>self.model.limits[n][3]+1e-6 for n,v in servo.items()):raise ValueError('transition optimization nonlinear servo residual')
        if result[205] not in (0.,1.) or not 0<=result[206]<=32 or result[204]>1e-7:
            raise ValueError('transition optimization native proof invalid')
        budget('exact_ik_validated');names=self._optimizer.names
        self.last_response=result[12:156].reshape(12,12).copy()
        self.last_model=dict(scope='spatial_spring_prediction_not_measured_force_or_torque',command_space=self.command_space,
            predicted_forces_world=dict(zip(feet,result[156:168].reshape(4,3).tolist())),
            predicted_joint_torques=dict(zip(names,result[168:180].tolist())),current_joint_torque_estimates=dict(zip(names,result[180:192].tolist())),
            entry_position_error_effort=dict(zip(names,result[192:204].tolist())),predicted_servo_command_efforts=servo,
            requested_delta_xyz=dict(zip(feet,delta.tolist())),future_geometry_validated=True,
            geometry_backend='native_reference_28_current_samples',geometry_library_sha256=self.geometry.provenance['library_sha256'],
            optimization_backend='qpmad_1_5_1_native',optimization_library_sha256=self._optimizer.provenance['library_sha256'],
            force_objective=self.force_objective,
            optimization_upstream_commit=UPSTREAM_COMMIT,linear_origin_feasible=bool(result[205]),vector_bound_method='inscribed_l1',
            inequality_residual=float(result[204]),optimization_iterations=int(result[206]),compute_wall_ns=time.perf_counter_ns()-start)
        return dict(zip(feet,delta.tolist()))
