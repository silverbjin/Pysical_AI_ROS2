"""Explicit book fixtures, separate from the verified continuous development rig."""
from dataclasses import asdict,dataclass
import math
import os
from types import MappingProxyType
import numpy as np
from scipy.spatial.transform import Rotation
from .fixture import TRANSPORT_CAMERA_POS,TRANSPORT_CAMERA_YAW_DEG,TRANSPORT_CAMERA_PITCH_UP_DEG


@dataclass(frozen=True)
class Scenario:
    name:str
    target_xyz:tuple
    receiving_xyz:tuple
    support_height_m:float
    camera_pos:tuple
    camera_yaw_deg:float
    camera_pitch_up_deg:float
    grasp_pitch_down_deg:float
    pre_distance_m:float
    approach_standoff_m:float|None
    world:str='empty'
    survey_pose:tuple|None=None
    approach_bearings:tuple|None=None

    @property
    def support_geom(self):return 'floor' if self.support_height_m==0. else 'reuse_receiving_support'
    @property
    def planning_support(self):return 'ground' if self.support_height_m==0. else 'reuse_receiving_support'
    @property
    def level(self):return 'continuous_development_fixture' if self.name=='development' else self.name
    def record(self):
        from .worlds import elements
        mode='experimental_se2' if self.name in ('level2_obstacles','level3_house') and os.environ.get('CH13_EXPERIMENTAL_SE2')=='1' else 'baseline_navfn'
        return dict(asdict(self),world_geometry=[g.record() for g in elements(self)],navigation_profile=mode)

    def receiving_support_ready(self,force,observation):
        if type(force) not in (int,float) or not math.isfinite(force) or force<=.01:return False
        if self.support_height_m>0:return True
        # Original observation freshness/owner checks remain in the lease.
        # Ground contact anywhere is not permission to release at the receiver.
        point=observation.get('point') if isinstance(observation,dict) else None
        try:
            return len(point)==3 and all(math.isfinite(v) for v in point) and math.dist(point[:2],self.receiving_xyz[:2])<.03
        except (TypeError,ValueError):return False


def _survey_pose(x,y,target=(3.,1.)):
    """Orient a map observation waypoint toward the known search region."""
    return (x,y,math.atan2(target[1]-y,target[0]-x))


SCENARIOS=MappingProxyType({
    'development':Scenario('development',(1.8,0.,.54),(-.8,0.,.54),.5,
        TRANSPORT_CAMERA_POS,TRANSPORT_CAMERA_YAW_DEG,TRANSPORT_CAMERA_PITCH_UP_DEG,0.,.12,None),
    'level1_floor':Scenario('level1_floor',(2.,0.,.04),(-.6,0.,.04),0.,(.4,.4,.29),-40.,-35.,30.,.06,.6),
    'level2_obstacles':Scenario('level2_obstacles',(3.,1.,.54),(-.8,0.,.54),.5,
        TRANSPORT_CAMERA_POS,TRANSPORT_CAMERA_YAW_DEG,TRANSPORT_CAMERA_PITCH_UP_DEG,0.,.12,.8,
        'obstacles',_survey_pose(1.65,-.3),(0.,)),
    'level3_house':Scenario('level3_house',(3.,1.,.04),(-.6,0.,.04),0.,(.4,.4,.29),-40.,-35.,30.,.03,.6,
        'house',_survey_pose(1.9,.4),(0.,)),
})


def get_scenario(name='development'):
    try:return SCENARIOS[name]
    except (KeyError,TypeError):raise ValueError('unknown validation scenario: '+str(name)) from None


def active_scenario():
    if os.environ.get('CH13_VALIDATION_PROFILE')!='carry_v1':return get_scenario()
    return get_scenario(os.environ.get('CH13_VALIDATION_SCENARIO','development'))


def grasp_pose(center,forward,sign,scenario):
    center=np.asarray(center,dtype=float);forward=np.asarray(forward,dtype=float)
    if (center.shape!=(3,) or forward.shape!=(3,) or not np.isfinite(center).all()
        or not np.isfinite(forward).all() or abs(forward[2])>1e-9 or np.linalg.norm(forward)<1e-6 or sign not in (-1.,1.)):
        raise ValueError('finite upright planar grasp geometry required')
    forward=forward/np.linalg.norm(forward);up=np.array([0.,0.,1.]);side=np.cross(up,forward)
    rotation=Rotation.from_matrix(np.column_stack((sign*up,-sign*side,forward)))
    if scenario.grasp_pitch_down_deg:
        rotation=Rotation.from_rotvec(side*math.radians(scenario.grasp_pitch_down_deg))*rotation
    return center-scenario.pre_distance_m*rotation.as_matrix()[:,2],rotation


def retreat_point(tcp,scenario):
    return (tcp[:3,3]-.08*tcp[:3,2] if scenario.grasp_pitch_down_deg else tcp[:3,3]+[.08,0.,0.])
