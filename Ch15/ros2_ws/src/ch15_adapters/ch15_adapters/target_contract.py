"""Position-only perception boundary. Never promote observations to grasp poses."""
import math
def check_metadata(rgb_stamp,depth_stamp,info_stamp,frame,depth_frame,info_frame,ros_ns,tf_ok,receipt_age):
    if not all(type(n) is int and n>0 for n in (rgb_stamp,depth_stamp,info_stamp,ros_ns)):return 'STAMP_INVALID'
    if max(abs(rgb_stamp-depth_stamp),abs(rgb_stamp-info_stamp))>50000000:return 'SYNC_SKEW'
    if any(n>ros_ns or ros_ns-n>300000000 for n in (rgb_stamp,depth_stamp,info_stamp)):return 'SOURCE_AGE'
    if not 0<=receipt_age<=.3:return 'RECEIPT_AGE'
    if not frame or frame!=depth_frame or frame!=info_frame or not tf_ok:return 'FRAME_OR_TF'
    return ''
def grasp_admissible(obs):
    return obs.get('valid') is True and obs.get('pose_kind')=='GRASP_POSE' and obs.get('source')=='MOCK'
