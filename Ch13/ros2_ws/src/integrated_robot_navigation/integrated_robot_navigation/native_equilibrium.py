"""Immutable URDF discrete-equilibrium arithmetic; no command authority."""
import ctypes,hashlib,json,weakref,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from ament_index_python.packages import get_package_prefix

def _pose(tag):
    value=np.eye(4)
    if tag is not None:
        value[:3,3]=np.fromstring(tag.get('xyz','0 0 0'),sep=' ')
        x,y,z=np.fromstring(tag.get('rpy','0 0 0'),sep=' ')
        cx,cy,cz=np.cos([x,y,z]);sx,sy,sz=np.sin([x,y,z])
        value[:3,:3]=[[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],
            [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]]
    return value.ravel().tolist()

def equilibrium_plan(urdf,*,joint_names=None):
    tree=ET.fromstring(urdf);joints=tree.findall('joint');parents={j.find('child').get('link') for j in joints}
    root=(set(l.get('name') for l in tree.findall('link'))-parents).pop()
    links={root:0};rows=[dict(parent=-1,origin=np.eye(4).ravel().tolist(),kind='fixed',axis=[0.,0.,0.],q=-1)]
    names=[];damping=[];gains=[];effort=[];pending=list(joints)
    while pending:
        ready=[j for j in pending if j.find('parent').get('link') in links]
        if not ready:raise ValueError('disconnected equilibrium model')
        for j in ready:
            kind=j.get('type');name=j.get('name');q=-1;axis=[0.,0.,0.]
            if kind!='fixed':
                if kind not in ('revolute','continuous','prismatic'):raise ValueError('unsupported equilibrium joint')
                q=len(names);names.append(name);axis=np.fromstring(j.find('axis').get('xyz'),sep=' ').tolist()
                dyn=j.find('dynamics');damping.append(float(dyn.get('damping','0')) if dyn is not None else 0.)
                kp=tree.find(f"ros2_control/joint[@name='{name}']/param[@name='ch13_kp']")
                if kp is None:raise ValueError('explicit PD gains required')
                gains.append(float(kp.text));effort.append(float(j.find('limit').get('effort')))
            child=j.find('child').get('link');links[child]=len(rows)
            rows.append(dict(parent=links[j.find('parent').get('link')],origin=_pose(j.find('origin')),kind=kind,axis=axis,q=q))
            pending.remove(j)
    for link in tree.findall('link'):
        row=rows[links[link.get('name')]];inertial=link.find('inertial')
        row.update(mass=0.,inertial=np.eye(4).ravel().tolist(),tensor=[0.]*9)
        if inertial is not None:
            tag=inertial.find('inertia');xx,yy,zz,xy,xz,yz=[float(tag.get(n)) for n in ('ixx','iyy','izz','ixy','ixz','iyz')]
            row.update(mass=float(inertial.find('mass').get('value')),inertial=_pose(inertial.find('origin')),tensor=[xx,xy,xz,xy,yy,yz,xz,yz,zz])
    feet=('fr_foot','fl_foot','rr_foot','rl_foot');legs=[f[:2]+'_'+p+'_joint' for f in feet for p in ('hip','thigh','calf')]
    if joint_names is not None:
        if len(joint_names)!=len(names) or set(joint_names)!=set(names):raise ValueError('equilibrium joint order')
        order=[names.index(name) for name in joint_names]
        for row in rows:
            if row['q']>=0:row['q']=order.index(row['q'])
        damping=[damping[i] for i in order];gains=[gains[i] for i in order];effort=[effort[i] for i in order];names=list(joint_names)
    return dict(nodes=rows,names=names,damping=damping,gains=gains,effort=effort,
        feet=[links[f] for f in feet],radii=[float(tree.find(f"link[@name='{f}']/collision/geometry/sphere").get('radius')) for f in feet],
        leg_indices=[names.index(n) for n in legs])

def equilibrium_library_path():
    return Path(get_package_prefix('integrated_robot_navigation_sensors'))/'lib/libnavigation_equilibrium.so'

class NativeEquilibrium:
    def __init__(self,urdf):
        self.plan=equilibrium_plan(urdf);self.names=tuple(self.plan['names']);self.nq=len(self.names)
        path=equilibrium_library_path()
        lib=ctypes.CDLL(str(path));ptr=ctypes.POINTER(ctypes.c_double)
        lib.ch13_equilibrium_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t];lib.ch13_equilibrium_create.restype=ctypes.c_void_p
        lib.ch13_equilibrium_destroy.argtypes=[ctypes.c_void_p];lib.ch13_equilibrium_destroy.restype=None
        lib.ch13_equilibrium_evaluate.argtypes=[ctypes.c_void_p,ptr,ctypes.c_size_t,ptr,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_size_t]
        lib.ch13_equilibrium_evaluate.restype=ctypes.c_int
        payload=json.dumps(self.plan,allow_nan=False).encode();error=ctypes.create_string_buffer(1024)
        handle=lib.ch13_equilibrium_create(payload,error,len(error))
        if not handle:raise ValueError('equilibrium plan: '+error.value.decode())
        self._library=lib;self._handle=handle;self._finalize=weakref.finalize(self,lib.ch13_equilibrium_destroy,handle)
        self.provenance=dict(library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),plan_sha256=hashlib.sha256(payload).hexdigest())

    def evaluate(self,*,joints,body_pose,command_joints,forces):
        if not self._finalize.alive:raise RuntimeError('equilibrium closed')
        values=np.ascontiguousarray([joints[n] for n in self.names]+[command_joints[n] for n in self.names]+list(np.asarray(body_pose).ravel())+list(np.asarray(forces).ravel()),dtype=np.float64)
        if values.size!=2*self.nq+28 or not np.isfinite(values).all():raise ValueError('equilibrium dimensions/finite input')
        output=np.empty(144+(self.nq+6)*12+4);ptr=ctypes.POINTER(ctypes.c_double);error=ctypes.create_string_buffer(1024)
        code=self._library.ch13_equilibrium_evaluate(self._handle,values.ctypes.data_as(ptr),values.size,output.ctypes.data_as(ptr),output.size,error,len(error))
        if code:raise ValueError('equilibrium: '+error.value.decode())
        return dict(force_derivative=output[:144].reshape(12,12).copy(),position_derivative=output[144:-4].reshape(self.nq+6,12).copy(),
            mass_kg=output[-4],linear_residual=output[-3],wall_ns=output[-2],cpu_ns=output[-1])

    def close(self):self._finalize()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
