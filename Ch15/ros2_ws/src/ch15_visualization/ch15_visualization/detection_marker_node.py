"""C16: observation marker; original header, position only, identity quaternion."""
from copy import deepcopy
from visualization_msgs.msg import Marker
from .marker_contract import TARGET_NS

def create_detection_marker(target, marker_id=0, label='', source='MOCK'):
    m=Marker()
    m.header=deepcopy(target.header)
    m.ns=TARGET_NS
    m.id=marker_id
    m.type=Marker.SPHERE
    m.action=Marker.ADD
    m.pose.position=deepcopy(target.pose.position)
    m.pose.orientation.w=1.0
    m.scale.x=m.scale.y=m.scale.z=0.08
    m.color.r,m.color.g,m.color.b,m.color.a=(0.1,0.8,0.2,0.9)
    m.text=f'{source} {label}'
    m.lifetime.sec=1
    return m

def delete_marker(frame,stamp,ns=TARGET_NS,marker_id=0):
    m=Marker()
    m.header.frame_id=frame
    m.header.stamp=stamp
    m.ns=ns
    m.id=marker_id
    m.action=Marker.DELETE
    return m
