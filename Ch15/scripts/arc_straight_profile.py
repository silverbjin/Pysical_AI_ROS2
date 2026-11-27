"""Measured-plant candidate. Isolated open-area qualification, not mission control."""
import math
RADIUS=.18
ANGLE=1.45
STRAIGHT=.20
ARC_W=-.10
ARC_V_FEED=.0125
ARC_CROSS_V_GAIN=.25
ARC_CROSS_W_GAIN=.8
ARC_W_MAX=-.07
ARC_V_MAX=.018
ARC_STOP_LEAD=.03
STRAIGHT_V=.035
STRAIGHT_STOP_LEAD=.007
STRAIGHT_SLIP_BIAS=.067
STRAIGHT_STOP_CROSS=.0065
STRAIGHT_BIAS_TAPER=.10
def wrap(x):return math.atan2(math.sin(x),math.cos(x))
def clip(x,lo,hi):return max(lo,min(hi,x))
def local(p,origin):
    dx,dy=p[0]-origin[0],p[1]-origin[1]
    c,s=math.cos(origin[2]),math.sin(origin[2])
    return dx*c+dy*s,-dx*s+dy*c,wrap(p[2]-origin[2])
def arc_point(theta):
    return RADIUS*math.sin(theta),-RADIUS*(1-math.cos(theta))
def arc_error(p):
    theta=clip(-p[2],0,ANGLE)
    x,y=arc_point(theta)
    ex,ey=x-p[0],y-p[1]
    return (math.hypot(ex,ey),ex*math.cos(theta)-ey*math.sin(theta),
            ex*math.sin(theta)+ey*math.cos(theta))
def arc_command(p):
    if not all(math.isfinite(x) for x in p):return None
    err,along,cross=arc_error(p)
    if -p[2]<-.08 or err>.05:
        return None
    if -p[2]>=ANGLE-ARC_STOP_LEAD:return (0.,0.)
    # Positive cross = robot inside the clockwise reference circle.
    # Increase forward contribution and reduce clockwise turn rate, bounded
    # by the same original 0.018 m/s and 0.10 rad/s command envelope.
    return (clip(ARC_V_FEED+.6*along+ARC_CROSS_V_GAIN*cross,0,ARC_V_MAX),
            clip(ARC_W+ARC_CROSS_W_GAIN*cross,ARC_W,ARC_W_MAX))
def arc_ready(p):
    return math.dist(p[:2],arc_point(ANGLE))<=.03 and abs(wrap(p[2]+ANGLE))<=.06
def final_target():
    x,y=arc_point(ANGLE)
    return x+STRAIGHT*math.cos(ANGLE),y-STRAIGHT*math.sin(ANGLE),-ANGLE
def straight_errors(p):
    x,y,h=final_target();dx,dy=x-p[0],y-p[1];c,s=math.cos(h),math.sin(h)
    return dx*c+dy*s,-dx*s+dy*c,wrap(h-p[2])
def straight_command(p):
    if not all(math.isfinite(x) for x in p):return None
    along,lateral,heading=straight_errors(p)
    if not -.025<=along<=.25 or abs(lateral)>.05 or abs(heading)>.12:return None
    if along<=STRAIGHT_STOP_LEAD:return (0.,0.)
    # Actual V2 straight body vy=-2.919mm/s, vx=43.594mm/s:
    # forward heading bias atan2(-vy,vx) ~=.067rad. Fade the bias
    # as the unchanged final goal approaches. The measured stationary
    # transition added +6.58mm cross error; anticipate that recoil.
    bias=STRAIGHT_SLIP_BIAS*clip((along-STRAIGHT_STOP_LEAD)/STRAIGHT_BIAS_TAPER,0,1)
    cross=clip(2*(lateral+STRAIGHT_STOP_CROSS),-.035,.035)
    return STRAIGHT_V,clip(.012+heading+cross+bias,-.05,.05)
def final_ready(p):
    g=final_target()
    return math.dist(p[:2],g[:2])<=.015 and abs(wrap(p[2]-g[2]))<=.06
