"""One current-input geometry batch; no cache, worker or command authority."""
import ctypes,hashlib,json,math,weakref
from pathlib import Path
import numpy as np
from ament_index_python.packages import get_package_prefix
from .compiled_reference import CompiledReferenceEnvelope


def reference_library_path():
    return Path(get_package_prefix('integrated_robot_navigation_sensors'))/'lib/libnavigation_reference_geometry.so'


class NativeReferenceEnvelope(CompiledReferenceEnvelope):
    def __init__(self,model,limits):
        super().__init__(model,limits)
        self._names=tuple(n for f in self.feet for n in self._legs[f].names)
        geometry=[]
        for f in self.feet:
            leg=self._legs[f]
            geometry.append(dict(hip=leg.hip,offset=leg.offset,upper=leg.upper,lower=leg.lower,
                physical=[v for pair in leg.physical for v in pair],allowed=[v for pair in leg.allowed for v in pair],
                half=leg.half,inverse=[v for row in leg.inverse for v in row],radius=leg.radius))
        payload=json.dumps(geometry,allow_nan=False).encode()
        path=reference_library_path()
        library=ctypes.CDLL(str(path));library.ch13_reference_abi_version.restype=ctypes.c_int
        if library.ch13_reference_abi_version()!=1:raise ValueError('native reference ABI mismatch')
        library.ch13_reference_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t]
        library.ch13_reference_create.restype=ctypes.c_void_p
        library.ch13_reference_destroy.argtypes=[ctypes.c_void_p];library.ch13_reference_destroy.restype=None
        pointer=ctypes.POINTER(ctypes.c_double)
        library.ch13_reference_evaluate.argtypes=[ctypes.c_void_p,pointer,ctypes.c_size_t,ctypes.c_int,pointer,ctypes.c_size_t]
        library.ch13_reference_evaluate.restype=ctypes.c_int
        error=ctypes.create_string_buffer(1024);handle=library.ch13_reference_create(payload,error,len(error))
        if not handle:raise ValueError('native reference plan: '+error.value.decode(errors='replace'))
        self._library=library;self._handle=handle
        self._finalize=weakref.finalize(self,library.ch13_reference_destroy,handle)
        self.provenance=dict(scope='current_geometry_arithmetic_no_state_or_command',abi=1,samples=28,
            library=str(path),library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            geometry_sha256=hashlib.sha256(payload).hexdigest(),model_sha256=model.model_sha256)

    def evaluate(self,*,joints,body,targets,envelope,selected,future_targets):
        if not self._finalize.alive:raise RuntimeError('native reference evaluator closed')
        if (selected not in self.feet or set(joints)!=set(self._joint_bounds)
                or any(set(v)!=set(self.feet) for v in (targets,envelope,future_targets))
                or any(not math.isfinite(joints[n]) or not a<=joints[n]<=b for n,(a,b) in self._joint_bounds.items())):
            raise ValueError('invalid current native reference input')
        pose=np.asarray(body,dtype=float)
        if pose.shape!=(4,4) or not np.isfinite(pose).all() or not np.allclose(pose[3],[0.,0.,0.,1.],atol=1e-12):
            raise ValueError('finite affine reference body required')
        try:inverse=np.linalg.inv(pose)
        except np.linalg.LinAlgError as error:raise ValueError('singular reference body') from error
        try:
            positions=np.asarray([targets[f] for f in self.feet],dtype=float)
            futures=np.asarray([future_targets[f] for f in self.feet],dtype=float)
            bounds=np.asarray([envelope[f] for f in self.feet],dtype=float)
            if positions.shape!=(4,3) or futures.shape!=(4,3) or bounds.shape!=(4,2):raise ValueError('reference dimensions')
            values=np.ascontiguousarray(np.r_[[joints[n] for n in self._names],inverse.ravel(),positions.ravel(),bounds.ravel(),futures.ravel()],dtype=np.float64)
        except (TypeError,OverflowError) as error:raise ValueError('invalid reference geometry') from error
        output=np.empty(40,dtype=np.float64);pointer=ctypes.POINTER(ctypes.c_double)
        code=self._library.ch13_reference_evaluate(self._handle,values.ctypes.data_as(pointer),len(values),
            self.feet.index(selected),output.ctypes.data_as(pointer),len(output))
        if code:raise ValueError('native reference geometry rejected: '+str(code))
        q=dict(joints);q.update(zip(self._names,output[:12]))
        return q,output[12:16].copy(),output[16:].copy()

    def close(self):self._finalize()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
