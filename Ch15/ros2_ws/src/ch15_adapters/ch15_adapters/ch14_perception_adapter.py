"""Read-only compatibility assessment, no model loading or ROS command APIs."""
import math
from .target_contract import check_metadata
def adapt(point,detections,*,target_class,model_sha,approved_sha,tf_at_source,ros_ns,confidence_min=.25,metadata=None):
    def blocked(reason):return dict(valid=False,source='UNKNOWN',pose_kind='UNKNOWN',reason='BLOCKED_COMPATIBILITY:'+reason)
    if not approved_sha or model_sha!=approved_sha or len(model_sha)!=64:return blocked('model_provenance')
    if not metadata or metadata.get('rgb_stamp')!=point.get('stamp') or check_metadata(metadata['rgb_stamp'],metadata['depth_stamp'],metadata['info_stamp'],metadata['frame'],metadata['depth_frame'],metadata['info_frame'],ros_ns,metadata['optical_tf'],metadata['receipt_age']):return blocked('rgbd_metadata')
    if point.get('frame')!='odom' or not tf_at_source:return blocked('frame_or_tf')
    stamp=point.get('stamp')
    if type(stamp) is not int or not 0<stamp<=ros_ns or ros_ns-stamp>300000000:return blocked('stamp')
    matches=[d for d in detections if d.get('class')==target_class and d.get('stamp')==stamp and d.get('frame')==metadata['frame']]
    if len(matches)!=1:return blocked('ambiguous_association')
    confidence=matches[0].get('confidence')
    if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not confidence_min<=confidence<=1.:return blocked('confidence')
    xyz=point.get('xyz',[])
    if len(xyz)!=3 or not all(math.isfinite(x) for x in xyz):return blocked('point')
    # tf_at_source is an audited transform callback, not a bool.
    if not callable(tf_at_source):return blocked('transform_not_supplied')
    try:result=tf_at_source(tuple(xyz),stamp,'odom','map')
    except Exception:return blocked('transform_failed')
    if len(result)!=3 or not all(math.isfinite(x) for x in result):return blocked('transform_nonfinite')
    return dict(valid=True,source='CH14_ORT',pose_kind='POSITION_ONLY',stamp=stamp,frame='map',xyz=list(result),confidence=confidence,orientation=[0,0,0,1],reason='')
