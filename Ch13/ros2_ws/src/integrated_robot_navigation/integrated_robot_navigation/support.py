"""Measured support geometry and mass-weighted kinematics, independent of ROS."""
import math
from functools import lru_cache
import xml.etree.ElementTree as ET

import numpy as np
from integrated_robot_vision.kinematics import KinematicChain

from .model import ModelContract
from .samples import JointMap, Vec3


def nearest_halfplane_point(matrix,bounds):
    """Minimum norm point in bounded-size 2D linear constraints A*x >= b.

    In two dimensions a minimum is the origin, one edge projection, or a
    two-edge intersection. Enumerate those finite cases; never relax a bound.
    """
    a,b=np.asarray(matrix,dtype=float),np.asarray(bounds,dtype=float)
    if (a.ndim!=2 or a.shape[1]!=2 or b.shape!=(len(a),) or not 1<=len(a)<=64
            or not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError('finite bounded 2D halfplanes required')
    points=[np.zeros(2)]
    norms=np.einsum('ij,ij->i',a,a)
    for i in range(len(a)):
        if norms[i]>1e-24:points.append(a[i]*b[i]/norms[i])
        for j in range(i):
            determinant=a[i,0]*a[j,1]-a[i,1]*a[j,0]
            if abs(determinant)>1e-12:
                points.append(np.array([b[i]*a[j,1]-a[i,1]*b[j],
                    a[i,0]*b[j]-b[i]*a[j,0]])/determinant)
    points=np.asarray(points)
    valid=points[np.all(a@points.T>=b[:,None]-1e-12,axis=0)]
    if not len(valid):raise ValueError('infeasible support halfplanes')
    return valid[np.argmin(np.einsum('ij,ij->i',valid,valid))].copy()


def support_margin(point: Vec3, contacts: list[Vec3]) -> float:
    p, points = np.asarray(point, dtype=float), np.asarray(contacts, dtype=float)
    if (p.shape != (3,) or points.ndim != 2 or points.shape[1] != 3
            or len(points) < 3 or not np.isfinite(p).all() or not np.isfinite(points).all()):
        raise ValueError('finite point and at least three contacts required')
    ordered = sorted(set(tuple(row[:2]) for row in points))
    if len(ordered) != len(points):
        raise ValueError('duplicate projected contact')

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    halves = []
    for sequence in (ordered, ordered[::-1]):
        half = []
        for contact in sequence:
            while len(half) >= 2 and cross(half[-2], half[-1], contact) <= 1e-12:
                half.pop()
            half.append(contact)
        halves.append(half[:-1])
    hull = halves[0] + halves[1]
    if len(hull) < 3:
        raise ValueError('degenerate support polygon')
    return float(min(cross(a, b, p) / math.hypot(b[0]-a[0], b[1]-a[1])
                     for a, b in zip(hull, hull[1:] + hull[:1])))


@lru_cache(maxsize=32)
def _mass_plan(urdf, mass_spec):
    """Compile immutable geometry, never a measured pose or joint value.

    Fixed descendants contribute mass-weighted first moments to their nearest
    moving ancestor. The runtime evaluates that ancestor once at the CURRENT q.
    Both URDF and exact mass data bind the bounded cache, including test models
    with replaced inertial data. No simulator mass or transform is changed.
    """
    tree=ET.fromstring(urdf);elements=tuple(tree.findall('joint'))
    compiled=KinematicChain(elements).compiled
    links={link.get('name') for link in tree.findall('link')}
    parents={joint.find('child').get('link'):(joint.find('parent').get('link'),spec)
        for joint,spec in zip(elements,compiled)}
    roots=links-set(parents)
    if len(roots)!=1:raise ValueError('one mass model root required')
    identity=np.eye(4);identity.setflags(write=False)
    frames={roots.pop():(None,identity)};visiting=set();plan=[]
    def frame(link):
        if link in frames:return frames[link]
        if link not in links or link in visiting:raise ValueError('invalid mass model topology')
        visiting.add(link)
        parent,spec=parents[link]
        owner,fixed=frame(parent)
        name,kind,origin,axis,skew,squared,bounds=spec
        fixed=fixed@origin;fixed.setflags(write=False)
        if kind!='fixed':
            for array in (axis,skew,squared):array.setflags(write=False)
            plan.append((name,owner,fixed,kind,axis,skew,squared,bounds))
            owner,fixed=name,identity
        frames[link]=(owner,fixed);visiting.remove(link)
        return frames[link]
    base_owner,base_fixed=frame('base_link')
    moments={};total=0.
    for link,mass,point in mass_spec:
        if not math.isfinite(mass) or mass<=0:raise ValueError('positive finite mass required')
        local=np.asarray((*point,1.),dtype=float)
        if local.shape!=(4,) or not np.isfinite(local).all():raise ValueError('finite inertial origin required')
        owner,fixed=frame(link)
        if owner not in moments:moments[owner]=np.zeros(4)
        moments[owner]+=fixed@(mass*local);total+=mass
    if total<=0:raise ValueError('model mass is empty')
    for moment in moments.values():moment.setflags(write=False)
    base_inverse=np.linalg.inv(base_fixed) if base_owner is None else None
    if base_inverse is not None:base_inverse.setflags(write=False)
    return tuple(plan),tuple(moments.items()),total,base_owner,base_fixed,base_inverse,identity


def center_of_mass(model: ModelContract, joints: JointMap, body_pose: object) -> Vec3:
    """body_pose is world_from_base_link, a rigid homogeneous 4x4 matrix."""
    pose = np.asarray(body_pose, dtype=float)
    if (pose.shape != (4, 4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3], (0., 0., 0., 1.), atol=1e-10)
            or not np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=1e-8)
            or not math.isclose(np.linalg.det(pose[:3, :3]), 1., abs_tol=1e-8)):
        raise ValueError('rigid body pose required')
    spec=tuple((link,mass,point if isinstance(point,tuple) else tuple(point))
        for link,(mass,point) in model.masses.items())
    plan,moments,total,base_owner,base_fixed,base_inverse,identity=_mass_plan(model.urdf,spec)
    frames={None:identity}
    for name,parent,origin,kind,axis,skew,squared,bounds in plan:
        if name not in joints:raise ValueError('missing named joint position')
        value=joints[name]
        if not math.isfinite(value) or bounds is not None and not bounds[0]<=value<=bounds[1]:
            raise ValueError('joint position outside finite limits')
        change=np.eye(4)
        if kind=='prismatic':change[:3,3]=axis*value
        else:change[:3,:3]+=math.sin(value)*skew+(1-math.cos(value))*squared
        frames[name]=frames[parent]@origin@change
    inverse=base_inverse if base_inverse is not None else np.linalg.inv(frames[base_owner]@base_fixed)
    root_moment=np.zeros(4)
    for owner,moment in moments:root_moment+=frames[owner]@moment
    world=pose@inverse@root_moment
    return tuple(float(v) for v in world[:3]/total)
