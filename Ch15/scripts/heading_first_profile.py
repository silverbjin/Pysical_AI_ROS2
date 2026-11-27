"""Ch15 heading-first candidate; independent of ROS."""
import math

OFFSET=.40
FINAL_XY=.015
FINAL_YAW=.06

def valid(p):
    return len(p)==3 and all(math.isfinite(x) for x in p)

def yaw_error(a,b):
    return abs(math.atan2(math.sin(a-b),math.cos(a-b)))

def stage(goal):
    if not valid(goal):raise ValueError("invalid goal")
    x,y,h=goal
    return (x-OFFSET*math.cos(h),y-OFFSET*math.sin(h),h)

def relative(p,g):
    dx,dy=p[0]-g[0],p[1]-g[1]
    c,s=math.cos(g[2]),math.sin(g[2])
    return dx*c+dy*s,-dx*s+dy*c

def aligned(p,g):
    if not valid(p) or not valid(g):return False
    along,lateral=relative(p,g)
    return math.dist(p[:2],stage(g)[:2])<=.06 and -.46<=along<=-.34 and abs(lateral)<=.03 and yaw_error(p[2],g[2])<=FINAL_YAW

def straight(p,g):
    if not aligned(p,g):raise ValueError("stage not aligned")
    n=math.ceil(math.dist(p[:2],g[:2])/.01)
    return [(p[0]+(g[0]-p[0])*i/n,p[1]+(g[1]-p[1])*i/n,g[2]) for i in range(n)]+[tuple(g)]

def corridor(p,g):
    if not valid(p) or not valid(g):return False
    a,b=relative(p,g)
    return -.48<=a<=.025 and abs(b)<=.05 and yaw_error(p[2],g[2])<=.12

def final(p,g):
    return valid(p) and valid(g) and math.dist(p[:2],g[:2])<=FINAL_XY and yaw_error(p[2],g[2])<=FINAL_YAW


def staging_guard(p,g,entered):
    """Latch a near-stage envelope; never let repeated fine alignment wander.

    The 100/120 mm values are candidate-only monitors, not a physical guarantee.
    """
    if not valid(p) or not valid(g):return False,entered
    d=math.dist(p[:2],stage(g)[:2])
    entered=entered or d<=.10
    return (not entered or d<=.12),entered
