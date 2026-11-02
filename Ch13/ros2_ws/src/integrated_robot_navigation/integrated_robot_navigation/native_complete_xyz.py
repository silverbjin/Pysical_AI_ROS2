"""One current-input contact/QP/geometry call, with the original wall cap.

Buffers and plan bindings belong to one numerical child, never a ROS callback.
There is no result cache, fallback, measurement substitution or motor authority.
The separate legacy wrapper remains an independent equivalence oracle.
"""
import ctypes
import math
import time
from time import thread_time_ns
import numpy as np
from .native_mass import _mass_spec
from .native_xyz import NativeXYZTransition, UPSTREAM_COMMIT


class CompleteXYZTransition(NativeXYZTransition):
    def __init__(self,model,limits,*,native_mass):
        super().__init__(model,limits,terms_evaluator=native_mass.contact_terms,
            force_objective='bounded_terminal_force')
        self.complete_kernel_closed=False
        try:
            self._mass=native_mass
            self._check_binding()
            if self._optimizer.names!=self.geometry._names:
                raise ValueError('complete XYZ leg order mismatch')
            lib=self._optimizer._library
            lib.ch13_xyz_complete_abi_version.restype=ctypes.c_int
            if lib.ch13_xyz_complete_abi_version()!=1:raise ValueError('complete XYZ ABI mismatch')
            ptr=ctypes.POINTER(ctypes.c_double)
            call=lib.ch13_xyz_complete_evaluate
            call.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ptr,ctypes.c_size_t,
                ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t),ctypes.c_size_t,ctypes.c_int,
                ctypes.c_double,ptr,ctypes.c_size_t,ptr,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_size_t]
            call.restype=ctypes.c_int
            self._call=call
            self._input=np.empty(len(native_mass.names)+127,dtype=np.float64)
            self._output=np.empty(220,dtype=np.float64)
            self._timings=np.zeros(12,dtype=np.float64)
            self._input_ptr=self._input.ctypes.data_as(ptr)
            self._output_ptr=self._output.ctypes.data_as(ptr)
            self._timing_ptr=self._timings.ctypes.data_as(ptr)
            self._error=ctypes.create_string_buffer(1024)
        except BaseException:
            self.close();raise

    def _check_binding(self):
        if (self.complete_kernel_closed or not self._optimizer._finalize.alive
                or not self.geometry._finalize.alive or not self._mass._finalize.alive):
            raise RuntimeError('complete XYZ plan closed')
        if (self.model.urdf!=self._mass._urdf or _mass_spec(self.model)!=self._mass._spec
                or tuple(self.model.feet)!=self._mass.feet):
            raise ValueError('complete XYZ model changed; reconfigure required')

    def prepare(self):
        self._check_binding()
        result=super().prepare()
        result.update(kernel_backend='native_complete_1',complete_kernel_abi=1)
        self.preparation=dict(result)
        return result

    def close(self):
        self.complete_kernel_closed=True
        super().close()  # the borrowed mass plan has a separate owner

    def step(self,*,foot,joints,body_pose,points,forces_world,target_forces,
             reference_xyz,origins,allowed_z,future_targets,dt,speed,min_force,
             command_joints=None,reference_pose=None):
        start=time.perf_counter_ns();cpu=thread_time_ns()
        self.last_model=None;self.last_response=None
        self.last_attempt=dict(scope='current_attempt_timing_not_force_measurement',stages={},
            preparation=self.preparation,command_space=self.command_space,
            optimization_backend='qpmad_1_5_1_native',force_objective=self.force_objective,
            kernel_backend='native_complete_1')
        self._check_binding();feet=self.model.feet
        if (foot not in feet or any(set(v)!=set(feet) for v in
                (points,forces_world,reference_xyz,origins,allowed_z,future_targets))
                or not set(target_forces).issubset(feet)
                or set(joints)!=set(self.geometry._joint_bounds)
                or any(not math.isfinite(joints[n]) or not a<=joints[n]<=b
                    for n,(a,b) in self.geometry._joint_bounds.items())
                or not all(math.isfinite(v) for v in (dt,speed,min_force))
                or not 0.<dt<=.2 or not 0.<speed<=self.limits['unload_speed_mps']
                or min_force!=self.limits['min_contact_force_n']):
            raise ValueError('invalid complete XYZ input')
        command=joints if command_joints is None else command_joints
        reference=body_pose if reference_pose is None else reference_pose
        # Fixed ABI order, one buffer, no intermediate numerical wrappers.
        # Shapes are checked before flattening; the C ABI validates every scalar.
        try:
            values=[joints[n] for n in self._mass.names]+[command[n] for n in self._optimizer.names]
            for pose in (body_pose,reference):
                if len(pose)!=4 or any(len(row)!=4 for row in pose):raise ValueError('pose dimensions')
                values.extend(v for row in pose for v in row)
            for mapping,width,default in ((points,3,None),(forces_world,3,None),
                    (target_forces,3,(0.,0.,0.)),(reference_xyz,3,None),
                    (origins,3,None),(allowed_z,2,None),(future_targets,3,None)):
                for f in feet:
                    row=mapping.get(f,default)
                    if len(row)!=width:raise ValueError('named vector dimensions')
                    values.extend(row)
            values.extend((dt,speed,min_force));self._input[:]=values
        except (KeyError,TypeError,OverflowError) as error:
            raise ValueError('invalid complete XYZ numeric input') from error
        offset_wall=time.perf_counter_ns()-start;offset_cpu=thread_time_ns()-cpu
        self.last_attempt['stages']['input_bounds']=dict(wall_ns=offset_wall,thread_cpu_ns=offset_cpu)
        if offset_wall>=10_000_000:
            self.last_attempt['rejected_at']='input_bounds';raise ValueError('transition optimization time budget')
        self._error.value=b''
        code=self._call(self._optimizer._handle,self._mass._handle,self.geometry._handle,
            self._input_ptr,len(self._input),len(self._mass.names),self._mass._contact_indices,12,
            feet.index(foot),10_000_000-offset_wall,self._output_ptr,len(self._output),
            self._timing_ptr,len(self._timings),self._error,len(self._error))
        for i,name in enumerate(('contact_terms','spatial_response','constraints_ready',
                'solver_finished','native_result_validated','exact_ik_validated')):
            w,c=self._timings[2*i:2*i+2]
            if w>0:self.last_attempt['stages'][name]=dict(wall_ns=int(offset_wall+w),thread_cpu_ns=int(offset_cpu+c))
        if code:
            self.last_attempt['native_error']=self._error.value.decode(errors='replace')
            self.last_attempt['rejected_at']='complete_native_call'
            raise ValueError('transition optimization complete XYZ: '+self.last_attempt['native_error']+' code='+str(code))
        result=self._output;names=self._optimizer.names
        delta=result[:12].reshape(4,3).tolist()
        servo=dict.fromkeys(self.model.joint_names,0.)
        servo.update(zip(names,result[208:220].tolist()))
        self.last_response=result[12:156].reshape(12,12).copy()
        proof=dict(scope='spatial_spring_prediction_not_measured_force_or_torque',command_space=self.command_space,
            predicted_forces_world=dict(zip(feet,result[156:168].reshape(4,3).tolist())),
            predicted_joint_torques=dict(zip(names,result[168:180].tolist())),
            current_joint_torque_estimates=dict(zip(names,result[180:192].tolist())),
            entry_position_error_effort=dict(zip(names,result[192:204].tolist())),
            predicted_servo_command_efforts=servo,requested_delta_xyz=dict(zip(feet,delta)),
            future_geometry_validated=True,geometry_backend='native_reference_28_current_samples',
            geometry_library_sha256=self.geometry.provenance['library_sha256'],
            optimization_backend='qpmad_1_5_1_native',optimization_library_sha256=self._optimizer.provenance['library_sha256'],
            force_objective=self.force_objective,optimization_upstream_commit=UPSTREAM_COMMIT,
            linear_origin_feasible=bool(result[205]),vector_bound_method='inscribed_l1',
            inequality_residual=float(result[204]),optimization_iterations=int(result[206]),
            kernel_backend='native_complete_1',complete_kernel_abi=1)
        wall=time.perf_counter_ns()-start
        self.last_attempt['stages']['complete_result_ready']=dict(wall_ns=wall,thread_cpu_ns=thread_time_ns()-cpu)
        if wall>10_000_000:
            self.last_response=None;self.last_attempt['rejected_at']='complete_result_ready'
            raise ValueError('transition optimization time budget')
        proof['compute_wall_ns']=wall;self.last_model=proof
        return dict(zip(feet,delta))
