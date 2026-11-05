"""One educational geometry definition for physics, planning and 2D occupancy."""
from dataclasses import asdict,dataclass
import math


@dataclass(frozen=True)
class Geometry:
    name:str
    center:tuple
    half:tuple
    pitch_deg:float=0.
    navigation_obstacle:bool=True
    terrain:bool=False

    @property
    def quat_wxyz(self):
        angle=math.radians(self.pitch_deg)/2
        return (math.cos(angle),0.,math.sin(angle),0.)

    def record(self):return dict(asdict(self),quat_wxyz=self.quat_wxyz)


def elements(scenario):
    if scenario.world=='empty':return ()
    if scenario.world not in ('obstacles','house'):raise ValueError('unknown world')
    height=.5 if scenario.world=='obstacles' else .9
    hx,hy=(.25,.30) if scenario.world=='obstacles' else (.45,.50)
    result=[Geometry('table_top',(3.,1.,height-.035),(hx,hy,.035),navigation_obstacle=False)]
    for i,(x,y) in enumerate(((-1,-1),(-1,1),(1,-1),(1,1))):
        result.append(Geometry('table_leg_'+str(i),(3.+x*(hx-.05),1.+y*(hy-.05),(height-.07)/2),
                               (.03,.03,(height-.07)/2)))
    if scenario.world=='obstacles':
        result.append(Geometry('box',(1.05,.45,.35),(.14,.20,.35)))
        angle=math.radians(5.);thickness=.03
        # Correct the box center so its *top face* spans the specified x endpoints.
        for name,mid,pitch in (('ramp_up',.575,-5.),('ramp_down',.825,5.)):
            p=math.radians(pitch)
            result.append(Geometry(name,(mid-thickness*math.sin(p),0.,.125*math.tan(angle)-thickness*math.cos(p)),
                (.125/math.cos(angle),1.5,thickness),pitch,False,True))
    else:
        for name,low,high in (('door_lower',-2.5,-.35),('door_upper',.75,2.5)):
            result.append(Geometry(name,(1.1,(low+high)/2,.6),(.04,(high-low)/2,.6)))
    return tuple(result)


def add_physics(spec,scenario):
    import mujoco
    for g in elements(scenario):
        spec.worldbody.add_geom(name='reuse_'+g.name,type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=g.center,size=g.half,quat=g.quat_wxyz,group=0 if g.terrain else 5,
            rgba=[.45,.42,.35,1.] if g.terrain else [.25,.30,.32,1.])


def planning_objects(scenario):
    from scipy.spatial.transform import Rotation
    from ch13_manipulation_reuse.planning import object_box,pose
    result=[]
    for g in elements(scenario):
        obj=object_box('reuse_'+g.name,g.center,[2*v for v in g.half])
        obj.primitive_poses=[pose(g.center,Rotation.from_euler('y',g.pitch_deg,degrees=True))]
        result.append(obj)
    return result
