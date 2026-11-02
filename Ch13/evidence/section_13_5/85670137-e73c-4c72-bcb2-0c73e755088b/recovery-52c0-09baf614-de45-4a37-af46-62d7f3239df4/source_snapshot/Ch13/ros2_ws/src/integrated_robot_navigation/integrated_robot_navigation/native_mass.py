"""One synchronous immutable-geometry arithmetic call; no runtime/ROS state.

The existing Python compiler still owns URDF validation and fixed-mass
aggregation. Only current-q matrix arithmetic crosses this versioned C ABI.
There is no fallback after an error, worker, measured-pose cache or command.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import weakref

import numpy as np
from ament_index_python.packages import get_package_prefix
from .support import _mass_plan


def _mass_spec(model):
    return tuple((link,mass,point if isinstance(point,tuple) else tuple(point))
        for link,(mass,point) in model.masses.items())


class NativeMassEvaluator:
    def __init__(self,model):
        self._urdf=model.urdf;self._spec=_mass_spec(model)
        plan,moments,total,base_owner,base_fixed,_,_=_mass_plan(self._urdf,self._spec)
        self.names=tuple(row[0] for row in plan)
        indices={None:0,**{name:i+1 for i,name in enumerate(self.names)}}
        geometry=dict(steps=[dict(parent=indices[parent],origin=origin.ravel().tolist(),
            kind=kind,axis=axis.tolist(),skew=skew.ravel().tolist(),squared=squared.ravel().tolist(),bounds=bounds)
            for name,parent,origin,kind,axis,skew,squared,bounds in plan],
            moments=[dict(owner=indices[owner],value=moment.tolist()) for owner,moment in moments],
            total=total,base_owner=indices[base_owner],base_fixed=base_fixed.ravel().tolist())
        path=Path(get_package_prefix('integrated_robot_navigation_sensors'))/'lib/libnavigation_mass_kinematics.so'
        library=ctypes.CDLL(str(path))
        library.ch13_mass_abi_version.restype=ctypes.c_int
        if library.ch13_mass_abi_version()!=1:raise ValueError('native mass ABI mismatch')
        library.ch13_mass_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t]
        library.ch13_mass_create.restype=ctypes.c_void_p
        library.ch13_mass_destroy.argtypes=[ctypes.c_void_p]
        library.ch13_mass_destroy.restype=None
        double_ptr=ctypes.POINTER(ctypes.c_double)
        library.ch13_mass_evaluate.argtypes=[ctypes.c_void_p,double_ptr,ctypes.c_size_t,double_ptr,double_ptr]
        library.ch13_mass_evaluate.restype=ctypes.c_int
        error=ctypes.create_string_buffer(1024)
        payload=json.dumps(geometry,allow_nan=False).encode()
        handle=library.ch13_mass_create(payload,error,len(error))
        if not handle:raise ValueError('native mass plan: '+error.value.decode(errors='replace'))
        self._library=library;self._handle=handle
        self._finalize=weakref.finalize(self,library.ch13_mass_destroy,handle)
        self.provenance=dict(scope='pure_current_q_mass_arithmetic_no_state_or_command',abi=1,
            library=str(path),library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            compiled_geometry_sha256=hashlib.sha256(payload).hexdigest(),joint_names=self.names,
            model_sha256=model.model_sha256)

    def __call__(self,model,joints,body_pose):
        if not self._finalize.alive:raise RuntimeError('native mass evaluator closed')
        if model.urdf!=self._urdf or _mass_spec(model)!=self._spec:
            raise ValueError('native mass model changed; reconfigure required')
        pose=np.ascontiguousarray(body_pose,dtype=np.float64)
        if pose.shape!=(4,4):raise ValueError('rigid body pose required')
        try:values=(ctypes.c_double*len(self.names))(*(joints[name] for name in self.names))
        except (KeyError,TypeError,OverflowError) as error:raise ValueError('invalid named joint position') from error
        output=(ctypes.c_double*3)()
        code=self._library.ch13_mass_evaluate(self._handle,values,len(values),
            pose.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),output)
        if code:raise ValueError({1:'native mass dimensions',2:'rigid body pose required',
            3:'joint position outside finite limits',4:'nonfinite mass result'}.get(code,'native mass failure'))
        return tuple(output)

    def close(self):self._finalize()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
