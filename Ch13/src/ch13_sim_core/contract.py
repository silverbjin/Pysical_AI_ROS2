"""Name-based immutable robot contract. All distances m, angles rad (REP-103)."""
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
import numpy as np
import yaml

@dataclass(frozen=True)
class JointGroup:
    names: tuple[str, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    nominal: tuple[float, ...]

@dataclass(frozen=True)
class RobotContract:
    groups: Mapping[str, JointGroup]
    mount_xyz: tuple[float, ...]
    mount_rpy: tuple[float, ...]

    @property
    def names(self): return tuple(n for g in self.groups.values() for n in g.names)
    @property
    def lower(self): return np.array([v for g in self.groups.values() for v in g.lower])
    @property
    def upper(self): return np.array([v for g in self.groups.values() for v in g.upper])
    @property
    def nominal(self): return np.array([v for g in self.groups.values() for v in g.nominal])

def ordered_values(names, values, expected_names) -> np.ndarray:
    names, expected = tuple(names), tuple(expected_names)
    data = np.asarray(values, dtype=float)
    if data.shape != (len(names),) or len(set(names)) != len(names) or not np.isfinite(data).all():
        raise ValueError('duplicate names, invalid shape or nonfinite values')
    if len(set(expected)) != len(expected) or not set(expected).issubset(names):
        raise ValueError('missing or duplicate expected joints')
    mapping = dict(zip(names, data))
    return np.array([mapping[n] for n in expected])

def load_contract(path: Path | None = None) -> RobotContract:
    resource = path if path is not None else files('ch13_sim_core').joinpath('data/joint_contract.yaml')
    raw = yaml.safe_load(resource.read_text(encoding='utf-8'))
    groups = {}
    if set(raw['groups']) != {'legs', 'arm', 'gripper'}:
        raise ValueError('expected legs, arm and gripper groups')
    for key, count in [('legs',12), ('arm',6), ('gripper',2)]:
        g = raw['groups'][key]
        names = tuple(g['names'])
        if len(names) != count or any(not isinstance(n,str) or not n for n in names):
            raise ValueError('invalid group names')
        arrays = [np.asarray(g[f],dtype=float) for f in ('lower','upper','nominal')]
        if any(a.shape != (count,) or not np.isfinite(a).all() for a in arrays):
            raise ValueError('invalid group dimensions/values')
        low, high, nominal = arrays
        if np.any(low >= high) or np.any(nominal < low) or np.any(nominal > high):
            raise ValueError('invalid joint limits/nominal')
        groups[key] = JointGroup(names, *(tuple(a) for a in arrays))
    mount = [tuple(raw['mount'][k]) for k in ('xyz','rpy')]
    if any(len(v) != 3 or not np.isfinite(v).all() for v in mount):
        raise ValueError('invalid mount')
    result = RobotContract(MappingProxyType(groups), *mount)
    if len(set(result.names)) != 20: raise ValueError('duplicate joint names')
    return result
