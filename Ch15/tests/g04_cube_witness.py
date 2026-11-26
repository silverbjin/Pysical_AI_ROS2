"""Separate actual DDS witness; world pose + analytic projection, never detector GT."""
import csv,itertools,json,math,pathlib,re,subprocess,sys,time
import numpy as np,cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image,CameraInfo
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rosgraph_msgs.msg import Clock
from cv_bridge import CvBridge
from ch15_interfaces.msg import TargetObservation
from ch15_adapters.qos_profiles import profile
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
cfg=json.loads(pathlib.Path(sys.argv[2]).read_text())
def run(*args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=8)
    if p.returncode!=0:raise RuntimeError('native command failed: '+p.stdout+p.stderr)
    return p.stdout
def model_pose(name):
    s=run('gz','model','-m',name,'-p')
    with (out/'model-pose.log').open('a') as f:f.write(name+'\n'+s+'\n')
    # gz model pose output contains XYZ and RPY triples, independent of RGB/depth.
    pairs=re.findall(r'\[\s*([-+0-9.eE]+)[,\s]+([-+0-9.eE]+)[,\s]+([-+0-9.eE]+)\s*\]',s)
    if len(pairs)<2:raise RuntimeError('cannot parse actual world pose: '+s)
    return np.array([float(v) for v in pairs[-2]+pairs[-1]])
def rpy(r,p,y):
    cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
    return np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])
def box_gt(cube,cam,k):
    # Gazebo camera x forward, y left, z up -> optical right/down/forward.
    optical_to_cam=np.array([[0,0,1],[-1,0,0],[0,-1,0]])
    rot=rpy(*cam[3:])@optical_to_cam
    vertices=np.array(list(itertools.product([-.025,.025],repeat=3)))@rpy(*cube[3:]).T+cube[:3]
    opt=(vertices-cam[:3])@rot
    assert np.all(opt[:,2]>0)
    u=k[0]*opt[:,0]/opt[:,2]+k[2];v=k[4]*opt[:,1]/opt[:,2]+k[5]
    return [float(u.min()),float(v.min()),float(u.max()),float(v.max())]
def iou(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=x*y
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)
def ns(m):return m.header.stamp.sec*1000000000+m.header.stamp.nanosec
rclpy.init();n=Node('ch15_cube_witness');maps={k:{} for k in ('rgb','depth','info','obs','diag','pose')};clock=[0];cv=CvBridge()
def rec(k,m):
    if k=='diag':m=json.loads(m.data);s=m['stamp_ns']
    else:s=ns(m)
    a=maps[k];a[s]=m
    while len(a)>100:a.pop(next(iter(a)))
subs=[]
for k,t,topic,q in [('rgb',Image,'/camera/image_raw',profile(20,reliable=False)),('depth',Image,'/camera/depth/image_raw',profile(20,reliable=False)),('info',CameraInfo,'/camera/camera_info',profile(20,reliable=False)),('obs',TargetObservation,'/ch15/target_observation',profile(20)),('diag',String,'/ch15/cube/diagnostics',profile(20)),('pose',PoseStamped,'/ch15/target_pose',profile(20))]:
    subs.append(n.create_subscription(t,topic,lambda m,k=k:rec(k,m),q))
subs.append(n.create_subscription(Clock,'/clock',lambda m:clock.__setitem__(0,m.clock.sec*1000000000+m.clock.nanosec),profile(20,reliable=False)))
def spin_until(pred,seconds=40):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        rclpy.spin_once(n,timeout_sec=.02)
        if pred():return
    raise RuntimeError('deadline; counts='+str({k:len(v) for k,v in maps.items()}))
def service(name):
    cl=n.create_client(Trigger,name);spin_until(cl.service_is_ready,5);f=cl.call_async(Trigger.Request());spin_until(f.done,5);assert f.result().success
def graph():
    names={name:len(n.get_publishers_info_by_topic(name)) for name in ('/cmd_vel','/ch15/cmd_vel_in','/ch13/reuse/cmd_vel_safe')}
    assert all(v==0 for v in names.values()),names
    return names
rows=[];err=None;cube=None;cam=None
def window(phase,count,after):
    seen=set();end=time.monotonic()+45
    while len(seen)<count and time.monotonic()<end:
        rclpy.spin_once(n,timeout_sec=.02)
        common=set.intersection(*(set(maps[k]) for k in ('rgb','depth','info','obs','diag')))
        for s in sorted(common):
            if s<=after or s in seen:continue
            rgb,d,info,o,diag=[maps[k][s] for k in ('rgb','depth','info','obs','diag')]
            if phase=='invalid_depth' and diag['fixture']!='invalid_depth':continue
            if phase!='invalid_depth' and diag['fixture']!='actual':continue
            if o.valid and s not in maps['pose']:continue
            seen.add(s);graph()
            row=dict(phase=phase,stamp_ns=s,rgb_stamp_ns=ns(rgb),depth_stamp_ns=ns(d),info_stamp_ns=ns(info),skew_ns=max(abs(ns(rgb)-ns(d)),abs(ns(rgb)-ns(info))),rgb_encoding=rgb.encoding,depth_encoding=d.encoding,valid=o.valid,reason=o.reason,pose_kind=o.pose_kind,source=o.source,gt_xyz=cube[:3].tolist())
            assert o.source=='RGBD_COLOR' and o.pose_kind=='POSITION_ONLY' and not o.has_confidence
            assert ns(o)==s and ns(o.target_pose)==s and o.header.frame_id=='map' and diag['valid']==o.valid and row['skew_ns']<=cfg['max_skew_ns']
            if phase=='normal':
                gt=box_gt(cube,cam,info.k);p=o.target_pose.pose.position;xyz=np.array([p.x,p.y,p.z])
                row.update(gt_bbox=gt,det_bbox=diag.get('bbox'),xyz=xyz.tolist(),error_m=float(np.linalg.norm(xyz-cube[:3])),iou=iou(diag['bbox'],gt) if o.valid else 0.)
                assert o.valid and row['error_m']<=cfg['max_center_error_m'] and row['iou']>=cfg['min_iou'],row
            else:
                assert not o.valid and s not in maps['pose'],row
                assert o.reason==('INVALID_DEPTH' if phase=='invalid_depth' else 'NO_UNIQUE_RED_COMPONENT'),row
            rows.append(row);print(json.dumps(row,allow_nan=False),flush=True)
            if len(seen)==1:
                cv2.imwrite(str(out/(phase+'-rgb.png')),cv.imgmsg_to_cv2(rgb,desired_encoding='bgr8'))
            if len(seen)==count:break
    assert len(seen)==count,(phase,len(seen))
    return max(seen)
try:
    spin_until(lambda:clock[0]>=1000000000 and len(maps['diag'])>=2)
    cube=model_pose('red_cube');cam=model_pose('rgbd_rig')
    spin_until(lambda:clock[0]>=2000000000)
    cube2=model_pose('red_cube')
    assert np.linalg.norm(cube2[:3]-cube[:3])<.001 and np.linalg.norm(cube2[:3]-np.array([2.,0.,.225]))<.005
    cube=cube2
    assert np.allclose(cam,np.array(cfg['camera_pose']),atol=1e-4)
    # Use only new unique post-settle stamps.
    last=window('normal',10,clock[0])
    service('/ch15/cube/invalid_depth_fixture')
    last=window('invalid_depth',3,max(last,clock[0]))
    service('/ch15/cube/normal_depth')
    s=run('gz','service','-s','/world/fetch_carry/set_pose','--reqtype','gz.msgs.Pose','--reptype','gz.msgs.Boolean','--timeout','3000','--req','name: "occlusion_screen" position { x: 1.3 y: 0 z: 0.37 } orientation { w: 1 }')
    (out/'occlusion-service.log').write_text(s);assert 'true' in s.lower()
    start=clock[0];spin_until(lambda:clock[0]>=start+1000000000)
    screen=model_pose('occlusion_screen');assert np.allclose(screen[:3],[1.3,0.,.37],atol=.005)
    window('occluded',3,clock[0]);graph()
except BaseException as exc:err=repr(exc);print('CUBE_FAIL',err,flush=True)
finally:
    (out/'positions.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    fields=['phase','stamp_ns','rgb_stamp_ns','depth_stamp_ns','info_stamp_ns','skew_ns','valid','reason','source','pose_kind','rgb_encoding','depth_encoding','gt_xyz','xyz','error_m','gt_bbox','det_bbox','iou']
    with (out/'positions.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    normal=[x for x in rows if x['phase']=='normal'];result=dict(result='PASS' if err is None and len(rows)==16 else 'FAIL',error=err,source='RGBD_COLOR',normal=len(normal),invalid_depth=sum(x['phase']=='invalid_depth' for x in rows),occluded=sum(x['phase']=='occluded' for x in rows),max_error_m=max((x['error_m'] for x in normal),default=None),min_iou=min((x['iou'] for x in normal),default=None),max_skew_ns=max((x['skew_ns'] for x in rows),default=None),command_publishers=graph(),full_mission_success=False)
    (out/'cube-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    n.destroy_node();rclpy.try_shutdown()
sys.exit(0 if result['result']=='PASS' else 1)
