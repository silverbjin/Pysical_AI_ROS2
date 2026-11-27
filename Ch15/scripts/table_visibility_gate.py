"""Static-target geometric visibility admission, not target tracking or authority."""
import math

OPTICAL=((0.,0.,1.),(-1.,0.,0.),(0.,-1.,0.))

def mm(a,b):return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def mv(a,b):return tuple(sum(a[i][k]*b[k] for k in range(3)) for i in range(3))
def rz(a):
    c,s=math.cos(a),math.sin(a);return ((c,-s,0),(s,c,0),(0,0,1))
def ry(a):
    c,s=math.cos(a),math.sin(a);return ((c,0,s),(0,1,0),(-s,0,c))
def project(point,base_xyz,quat,cam_pos,yaw_deg,pitch_deg,calibration):
    values=(*point,*base_xyz,*quat,*cam_pos,yaw_deg,pitch_deg,*calibration)
    if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite projection input')
    x,y,z,w=quat
    if abs(x*x+y*y+z*z+w*w-1)>.001:raise ValueError('invalid quaternion')
    b=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),(2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),(2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
    r=mm(b,mm(mm(rz(math.radians(yaw_deg)),ry(math.radians(-pitch_deg))),OPTICAL))
    offset=mv(b,cam_pos);delta=[point[i]-base_xyz[i]-offset[i] for i in range(3)]
    q=[sum(r[j][i]*delta[j] for j in range(3)) for i in range(3)]
    fx,fy,cx,cy=calibration
    if fx<=0 or fy<=0 or (round(2*cx+1),round(2*cy+1))!=(320,240) or q[2]<=.1:raise ValueError('invalid optical projection')
    def px(p):return (fx*p[0]/p[2]+cx,fy*p[1]/p[2]+cy)
    # Conservative bounding cube around known upright 40mm diameter/80mm height.
    radius=.045
    corners=[px((q[0]+a*radius,q[1]+b*radius,q[2]+c*radius)) for a in (-1,1) for b in (-1,1) for c in (-1,1)]
    u,v=px(q);lo=(min(a for a,b in corners),min(b for a,b in corners));hi=(max(a for a,b in corners),max(b for a,b in corners))
    return dict(center_px=(u,v),depth_m=q[2],bounds=(lo,hi),full_frame=bool(lo[0]>=2 and lo[1]>=2 and hi[0]<=317 and hi[1]<=237))

class VisibilityGate:
    def __init__(self):self.enter=None;self.seen=False
    def check(self,now,*,full_frame,health,fresh,shift):
        if not health:return False,'CAMERA_HEALTH_EXPIRED'
        if fresh and (shift is None or not math.isfinite(shift) or shift>=.03):return False,'TARGET_MOVED'
        if not full_frame:
            self.enter=None;self.seen=False
            return True,'OBSERVED_EDGE' if fresh else 'GEOMETRIC_BLIND'
        if self.enter is None:self.enter=now;self.seen=False
        if fresh:self.seen=True;return True,'OBSERVED'
        if self.seen or now-self.enter>.3:return False,'TARGET_NOT_REACQUIRED'
        return True,'REACQUIRING'
