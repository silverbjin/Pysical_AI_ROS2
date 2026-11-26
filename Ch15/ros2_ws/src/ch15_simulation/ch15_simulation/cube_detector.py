"""Frozen HSV and median-depth position-only detector. No command output."""
import math
import numpy as np
import cv2

def locate(bgr,depth_m,k):
    if bgr.ndim!=3 or bgr.shape[2]!=3 or depth_m.shape!=bgr.shape[:2]:return None,'SHAPE'
    if len(k)!=9 or not np.isfinite(k).all() or k[0]<=0 or k[4]<=0:return None,'INTRINSICS'
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,np.array([0,100,50],np.uint8),np.array([10,255,255],np.uint8)) | cv2.inRange(hsv,np.array([170,100,50],np.uint8),np.array([179,255,255],np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contours=[c for c in contours if cv2.contourArea(c)>=25]
    if len(contours)!=1:return None,'NO_UNIQUE_RED_COMPONENT'
    c=contours[0];x,y,w,h=cv2.boundingRect(c)
    component=np.zeros(mask.shape,np.uint8);cv2.drawContours(component,[c],0,255,-1)
    valid=(component>0)&(mask>0)&np.isfinite(depth_m)&(depth_m>=.05)&(depth_m<=5.)
    if np.count_nonzero(valid)<25 or np.count_nonzero(valid)<.5*np.count_nonzero(component):return None,'INVALID_DEPTH'
    surface=float(np.median(depth_m[valid]));u=x+(w-1)/2.;v=y+(h-1)/2.
    # Known 5 cm cube: half-edge correction along optical ray, not measured grasp orientation.
    z=surface+.025
    optical=np.array([(u-k[2])*z/k[0],(v-k[5])*z/k[4],z],float)
    return dict(bbox=[x,y,x+w,y+h],optical=optical.tolist(),surface_depth_m=surface,valid_depth_pixels=int(valid.sum())),''

def rotation(q):
    x,y,z,w=q
    if not np.isfinite(q).all() or abs(x*x+y*y+z*z+w*w-1)>1e-5:raise ValueError('TF_QUATERNION')
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def main():
    import json,time
    from collections import OrderedDict
    import rclpy
    from rclpy.node import Node
    from rclpy.time import Time
    from rclpy.clock import Clock,ClockType
    from sensor_msgs.msg import Image,CameraInfo
    from geometry_msgs.msg import PoseStamped
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
    from cv_bridge import CvBridge
    from tf2_ros import Buffer,TransformListener
    from ch15_interfaces.msg import TargetObservation
    from ch15_adapters.target_contract import check_metadata
    from ch15_adapters.qos_profiles import profile
    def stamp(m):return m.header.stamp.sec*1000000000+m.header.stamp.nanosec
    class Detector(Node):
        def __init__(self):
            super().__init__('ch15_cube_detector')
            self.cv=CvBridge();self.maps={k:OrderedDict() for k in ('rgb','depth','info')};self.last=0
            self.invalid_fixture=False;self.fixture_allowed=self.declare_parameter('allow_invalid_depth_fixture',False).value
            self.tf=Buffer();self.listener=TransformListener(self.tf,self)
            for key,typ,topic in [('rgb',Image,'/camera/image_raw'),('depth',Image,'/camera/depth/image_raw'),('info',CameraInfo,'/camera/camera_info')]:
                self.create_subscription(typ,topic,lambda m,k=key:self.receive(k,m),profile(10,reliable=False))
            self.target=self.create_publisher(TargetObservation,'/ch15/target_observation',profile())
            self.pose=self.create_publisher(PoseStamped,'/ch15/target_pose',profile())
            self.diag=self.create_publisher(String,'/ch15/cube/diagnostics',profile(20))
            self.create_service(Trigger,'/ch15/cube/invalid_depth_fixture',self.set_invalid)
            self.create_service(Trigger,'/ch15/cube/normal_depth',self.set_normal)
            self.create_timer(.02,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
        def set_invalid(self,req,res):
            res.success=self.fixture_allowed
            if res.success:self.invalid_fixture=True
            res.message='explicit copied real depth invalidation' if res.success else 'fixture disabled';return res
        def set_normal(self,req,res):
            self.invalid_fixture=False;res.success=True;return res
        def receive(self,key,msg):
            s=stamp(msg);a=self.maps[key];a[s]=(msg,time.monotonic())
            while len(a)>20:a.popitem(last=False)
        def tick(self):
            now=time.monotonic();ros=self.get_clock().now().nanoseconds
            common=set(self.maps['rgb'])&set(self.maps['depth'])&set(self.maps['info'])
            pending=sorted(s for s in common if self.last<s<=ros)
            if not pending:return
            s=pending[0];self.last=s
            (rgb,a),(depth,b),(info,c)=[self.maps[k].pop(s) for k in ('rgb','depth','info')]
            frame=rgb.header.frame_id
            row=dict(stamp_ns=s,rgb_stamp_ns=stamp(rgb),depth_stamp_ns=stamp(depth),info_stamp_ns=stamp(info),frame=frame,depth_frame=depth.header.frame_id,info_frame=info.header.frame_id,depth_encoding=depth.encoding,rgb_encoding=rgb.encoding,ros_ns=ros,receipt_age_s=now-min(a,b,c),fixture='invalid_depth' if self.invalid_fixture else 'actual',valid=False,pose_kind='POSITION_ONLY',source='RGBD_COLOR')
            reason='';result=None;world=None;tf=None
            try:
                tf=self.tf.lookup_transform('map',frame,Time.from_msg(rgb.header.stamp))
            except Exception:pass
            reason=check_metadata(stamp(rgb),stamp(depth),stamp(info),frame,depth.header.frame_id,info.header.frame_id,ros,tf is not None,now-min(a,b,c))
            if not reason:
                try:
                    image=self.cv.imgmsg_to_cv2(rgb,desired_encoding='bgr8');d=self.cv.imgmsg_to_cv2(depth,desired_encoding='passthrough')
                    if depth.encoding=='16UC1':d=d.astype(np.float32)*.001
                    elif depth.encoding=='32FC1':d=d.astype(np.float32,copy=True)
                    else:raise ValueError('DEPTH_ENCODING')
                    if self.invalid_fixture:d[:]=np.nan
                    result,reason=locate(image,d,info.k)
                    if result:
                        p=tf.transform.translation;q=tf.transform.rotation
                        world=rotation([q.x,q.y,q.z,q.w])@np.array(result['optical'])+np.array([p.x,p.y,p.z])
                        if not np.isfinite(world).all():raise ValueError('NONFINITE_WORLD')
                except Exception as exc:reason=str(exc);result=None;world=None
            obs=TargetObservation();obs.header.stamp=rgb.header.stamp;obs.header.frame_id='map';obs.mission_id='cube_lab';obs.epoch=0;obs.source='RGBD_COLOR';obs.object_class='red_cube';obs.pose_kind='POSITION_ONLY';obs.target_pose.header=obs.header;obs.target_pose.pose.orientation.w=1.;obs.valid=result is not None and world is not None and not reason;obs.reason=reason;obs.has_confidence=False
            if obs.valid:
                obs.target_pose.pose.position.x,obs.target_pose.pose.position.y,obs.target_pose.pose.position.z=map(float,world)
                row.update(result,xyz=world.tolist(),valid=True)
                self.pose.publish(obs.target_pose)
            row['reason']=reason;self.target.publish(obs);self.diag.publish(String(data=json.dumps(row,allow_nan=False)))
    rclpy.init();node=Detector()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
