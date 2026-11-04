"""Load middleware type support before entering the short live lease boundary."""
import importlib
import time


def prepare_manipulation_types(*,check=None):
    if check is None:
        from rclpy.type_support import check_for_type_support
        check=check_for_type_support
    records=[]
    # run_pick imports the warmup lazily. Its first import is also startup work.
    started=time.monotonic();importlib.import_module('run_arm_probe')
    records.append(dict(step='import_run_arm_probe',start_wall=started,end_wall=time.monotonic(),
        scope='initialization_only_no_client_or_goal'))
    for module,names in (
        ('control_msgs.action',('FollowJointTrajectory','GripperCommand')),
        ('nav2_msgs.action',('NavigateToPose',)),
        ('moveit_msgs.srv',('GetMotionPlan','GetCartesianPath','ApplyPlanningScene','GetPlanningScene'))):
        for name in names:
            started=time.monotonic();check(getattr(importlib.import_module(module),name))
            records.append(dict(step='type_support:'+name,start_wall=started,end_wall=time.monotonic(),
                scope='initialization_only_no_client_or_goal'))
    return records
