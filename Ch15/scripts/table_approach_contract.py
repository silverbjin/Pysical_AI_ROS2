"""Fixed-world V3 geometry and one-way handoff admission; no ROS actuation."""
import math
from arc_straight_profile import ANGLE,RADIUS,STRAIGHT,arc_point,final_target,local,wrap


def world(p,origin):
    c,s=math.cos(origin[2]),math.sin(origin[2])
    return origin[0]+c*p[0]-s*p[1],origin[1]+s*p[0]+c*p[1],wrap(origin[2]+p[2])


def entry_for(goal):
    if len(goal)!=3 or not all(math.isfinite(v) for v in goal):raise ValueError('invalid goal')
    h=wrap(goal[2]+ANGLE)
    x,y,_=world(final_target(),(0.,0.,h))
    return goal[0]-x,goal[1]-y,h


def segment(a,b):
    d=math.dist(a[:2],b[:2]);h=wrap(b[2]-a[2]);n=max(1,math.ceil(d/.005),math.ceil(abs(h)/math.radians(1)))
    return [(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n,wrap(a[2]+h*i/n)) for i in range(n+1)]


def route(start,goal):
    if len(start)!=3 or not all(math.isfinite(v) for v in start):raise ValueError('invalid start')
    e=entry_for(goal);b=math.atan2(e[1]-start[1],e[0]-start[0])
    if math.dist(start[:2],e[:2])<.1 or abs(wrap(b-e[2]))>.04:raise ValueError('entry tangent mismatch')
    n=max(math.ceil(RADIUS*ANGLE/.005),math.ceil(ANGLE/math.radians(1)))
    arc=[world((*arc_point(ANGLE*i/n),-ANGLE*i/n),e) for i in range(n+1)]
    return {'entry':e,'initial_turn':segment(start,(*start[:2],b)),
            'travel':segment((*start[:2],b),e),'arc':arc,'straight':segment(arc[-1],goal)}


def entry_ready(p,entry):
    q=local(p,entry)
    return all(math.isfinite(v) for v in q) and math.hypot(*q[:2])<=.03 and abs(q[2])<=.06


class Handoff:
    """One-way state only. Runtime must supply live, independently audited proof."""
    def __init__(self):self.owner='NAV2'
    def switch(self,*,goal_terminal,goal_active,stationary,boundary_phase,entry_ok,chain_ok,fault):
        if self.owner!='NAV2' or goal_terminal!=4 or goal_active is not False or stationary is not True or boundary_phase!='IDLE' or entry_ok is not True or chain_ok is not True or fault is not False:
            raise RuntimeError('handoff refused')
        self.owner='V3'
