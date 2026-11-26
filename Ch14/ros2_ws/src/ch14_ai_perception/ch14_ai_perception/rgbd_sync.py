"""Validate aligned RGB-D pair, calibrated axial Z and source-stamped TF."""
import numpy as np
from .depth_geometry.contracts import Box2D,Intrinsics
from .depth_geometry.geometry import decode_depth,sample_depth,deproject,transform_point

def ns(header):
    return int(header.stamp.sec)*1_000_000_000+int(header.stamp.nanosec)

def validate_pair(rgb,depth,info):
    stamps=[ns(x.header) for x in (rgb,depth,info)]
    if min(stamps)<=0 or max(stamps)-min(stamps)>50_000_000:raise ValueError("RGBD_SKEW")
    frame=rgb.header.frame_id
    if not frame or not all(x.header.frame_id==frame for x in (depth,info)):
        raise ValueError("RGBD_FRAME")
    if not all((x.width,x.height)==(rgb.width,rgb.height) for x in (depth,info)):
        raise ValueError("RGBD_DIMENSIONS")
    k=info.k
    if len(k)!=9 or not np.isfinite(k).all() or not np.allclose([k[1],k[3],k[6],k[7],k[8]],[0,0,0,0,1]):
        raise ValueError("CAMERA_K")
    if any(abs(v)>1e-9 for v in info.d) or info.binning_x not in (0,1) or info.binning_y not in (0,1):
        raise ValueError("UNRECTIFIED_OR_BINNED_CAMERA")
    if any(getattr(info.roi,n) for n in ("x_offset","y_offset","width","height")):raise ValueError("ROI_UNSUPPORTED")
    if not (0<=k[2]<rgb.width and 0<=k[5]<rgb.height):raise ValueError("PRINCIPAL_POINT")
    intr=Intrinsics(rgb.width,rgb.height,k[0],k[4],k[2],k[5],frame,"camera_info")
    z=decode_depth(bytes(depth.data),depth.encoding,depth.width,depth.height,depth.step,bool(depth.is_bigendian))
    return intr,z

def point_from_detection(d,intr,depth):
    x1,y1,x2,y2=d.xyxy
    box=Box2D((x1+x2)/2,(y1+y2)/2,x2-x1,y2-y1,str(d.class_id),d.confidence)
    z,mad=sample_depth(depth,box)
    return deproject(box.cx,box.cy,z,intr),mad

def transform_matrix(t):
    q=t.rotation;v=np.array([q.x,q.y,q.z,q.w],dtype=float)
    if not np.isfinite(v).all() or not np.isclose(np.linalg.norm(v),1.,atol=1e-6):raise ValueError("TF_QUATERNION")
    x,y,z,w=v/np.linalg.norm(v)
    m=np.eye(4)
    m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
              [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
              [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    m[:3,3]=[t.translation.x,t.translation.y,t.translation.z]
    return m
