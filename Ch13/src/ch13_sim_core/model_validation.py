"""Validate declared joint axes/limits and mount, before engine compilation."""
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

@dataclass(frozen=True)
class JointSpec:
    axis: tuple[float, ...]
    lower: float
    upper: float

class ModelJoints(dict):
    def __init__(self, *args, mount_xyz, mount_rpy):
        super().__init__(*args)
        self.mount_xyz, self.mount_rpy = mount_xyz, mount_rpy

def vector(text): return tuple(float(v) for v in text.split())

def load_urdf_joints(xml_text: str) -> dict[str, JointSpec]:
    root = ET.fromstring(xml_text)
    mount = root.find("joint[@name='arm_mount_fixed']/origin")
    result = ModelJoints(mount_xyz=vector(mount.get('xyz')), mount_rpy=vector(mount.get('rpy','0 0 0')))
    for j in root.findall('joint'):
        if j.get('type') == 'fixed': continue
        n = j.get('name')
        if n in result: raise ValueError('duplicate '+n)
        limit = j.find('limit')
        result[n] = JointSpec(vector(j.find('axis').get('xyz')), float(limit.get('lower')), float(limit.get('upper')))
    return result

def load_mjcf_joints(path: Path) -> dict[str, JointSpec]:
    root = ET.parse(path).getroot()
    mount = root.find(".//body[@name='arm_mount']")
    result = ModelJoints(mount_xyz=vector(mount.get('pos')),mount_rpy=vector(mount.get('euler','0 0 0')))
    for j in root.findall('.//worldbody//joint'):
        if j.get('type') == 'free': continue
        n = j.get('name')
        if n in result: raise ValueError('duplicate '+n)
        low, high = vector(j.get('range'))
        result[n] = JointSpec(vector(j.get('axis')),low,high)
    actuators = root.findall('actuator/*')
    if len(actuators) != len(result) or {a.get('joint') for a in actuators} != set(result):
        raise ValueError('actuator contract mismatch')
    return result

def validate_model_parity(contract, urdf, mjcf) -> None:
    if set(urdf) != set(contract.names) or set(mjcf) != set(contract.names):
        raise ValueError('joint names mismatch')
    for model in (urdf,mjcf):
        if not np.allclose(model.mount_xyz,contract.mount_xyz,atol=1e-8,rtol=0) or not np.allclose(model.mount_rpy,contract.mount_rpy,atol=1e-8,rtol=0):
            raise ValueError('mount mismatch')
    for i,name in enumerate(contract.names):
        u,m = urdf[name],mjcf[name]
        if not np.allclose(u.axis,m.axis,atol=1e-8,rtol=0) or not np.allclose([u.lower,u.upper,m.lower,m.upper],[contract.lower[i],contract.upper[i]]*2,atol=1e-8,rtol=0):
            raise ValueError('axis/limit mismatch '+name)
