"""Python picking API over one authoritative MoveGroup planning scene.

Uses actual Jazzy services/actions instead of nonexistent MoveItPy Cartesian
methods. This is a MoveIt service wrapper, not moveit_commander or fake hardware.
"""
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rclpy.action import ActionClient
from geometry_msgs.msg import Pose,PoseStamped
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import (CollisionObject,Constraints,JointConstraint,PositionConstraint,
    OrientationConstraint,PlanningScene,PlanningSceneComponents,AllowedCollisionEntry,AttachedCollisionObject)
from moveit_msgs.srv import GetMotionPlan,GetCartesianPath,ApplyPlanningScene,GetPlanningScene
from control_msgs.action import FollowJointTrajectory
from .action_bridge import ARM
from rosidl_runtime_py.convert import message_to_ordereddict
from ament_index_python.packages import get_package_share_directory
from .trajectory import JOINTS
from .model import urdf_fk
from .planning_contract import execution_admission,cartesian_complete
from .retime import normalize_points


def pose(position,rotation=None):
    result=Pose();result.position.x,result.position.y,result.position.z=map(float,position)
    q=Rotation.identity().as_quat() if rotation is None else rotation.as_quat()
    result.orientation.x,result.orientation.y,result.orientation.z,result.orientation.w=map(float,q)
    return result


def object_box(name,center,dimensions):
    result=CollisionObject();result.id=name;result.header.frame_id='reuse/odom'
    primitive=SolidPrimitive();primitive.type=SolidPrimitive.BOX;primitive.dimensions=list(map(float,dimensions))
    result.primitives=[primitive];result.primitive_poses=[pose(center)];result.operation=CollisionObject.ADD
    return result


def object_cylinder(name,center,radius=.02,height=.08):
    result=CollisionObject();result.id=name;result.header.frame_id='reuse/odom'
    result.primitives=[SolidPrimitive(type=SolidPrimitive.CYLINDER,dimensions=[height,radius])]
    result.primitive_poses=[pose(center)];result.operation=CollisionObject.ADD
    return result


class Planner:
    def __init__(self,node,until,snapshot,action_client_factory=ActionClient):
        self.node,self.until,self.snapshot=node,until,snapshot
        self.clients={};self.revision=0;self.records=[]
        self.compute_worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='reuse_planning_validation')
        def initialized(step,start):
            self.records.append(dict(kind='initialization',step=step,start_wall=start,end_wall=time.monotonic()))
        # A cold filesystem lookup/read can exceed the live lease's 300ms.
        # Reuse the bounded compute worker while the sole ROS owner polls.
        try:
            start=time.monotonic()
            self.description=self.compute(lambda:(Path(get_package_share_directory('ch13_piper_moveit_config'))/'config/robot.urdf').read_text())
            initialized('description_read_with_owner_poll',start)
        except BaseException:
            self.compute_worker.shutdown(wait=True,cancel_futures=True)
            raise
        start=time.monotonic();self.execution=action_client_factory(node,FollowJointTrajectory,ARM)
        initialized('arm_client_creation',start)
        for typ,name in [(GetMotionPlan,'/plan_kinematic_path'),(GetCartesianPath,'/compute_cartesian_path'),
                         (ApplyPlanningScene,'/apply_planning_scene'),(GetPlanningScene,'/get_planning_scene')]:
            start=time.monotonic();client=node.create_client(typ,name);self.clients[name]=client
            initialized('service_client_creation:'+name,start)
            assert until(client.service_is_ready,10.),'MoveIt service unavailable: '+name
        assert until(self.execution.server_is_ready,3.),'MoveIt trajectory execution unavailable'

    def call(self,name,request,timeout=8.):
        future=self.clients[name].call_async(request)
        assert self.until(future.done,timeout),'MoveIt service response deadline: '+name
        return future.result()

    def compute(self,callback):
        future=self.compute_worker.submit(callback)
        assert self.until(future.done,5.),'planning adapter computation deadline'
        return future.result()

    def start_state(self):
        from moveit_msgs.msg import RobotState
        state=RobotState();state.is_diff=True;state.joint_state=self.snapshot()['joints']
        return state

    def joints(self):
        current=self.snapshot()['joints'];values=dict(zip(current.name,current.position))
        return np.array([values[j] for j in JOINTS])

    def tcp(self,positions=None):
        current=self.snapshot();js=current['joints'];values=dict(zip(js.name,js.position))
        if positions is not None:values.update(zip(JOINTS,positions))
        fk=urdf_fk(self.description,values)['reuse/tcp']
        base=current['state'].pose.pose;root=np.eye(4)
        root[:3,3]=[base.position.x,base.position.y,base.position.z]
        root[:3,:3]=Rotation.from_quat([base.orientation.x,base.orientation.y,base.orientation.z,base.orientation.w]).as_matrix()
        return root@fk

    def scene_hash(self):
        request=GetPlanningScene.Request()
        request.components.components=(PlanningSceneComponents.WORLD_OBJECT_GEOMETRY|PlanningSceneComponents.ALLOWED_COLLISION_MATRIX|PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
        scene=self.call('/get_planning_scene',request).scene
        value=dict(world=message_to_ordereddict(scene.world),acm=message_to_ordereddict(scene.allowed_collision_matrix),
                   attached=[message_to_ordereddict(x) for x in scene.robot_state.attached_collision_objects])
        return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

    def apply_objects(self,objects):
        request=ApplyPlanningScene.Request();request.scene.is_diff=True;request.scene.robot_state.is_diff=True
        request.scene.world.collision_objects=objects
        assert self.call('/apply_planning_scene',request).success,'planning scene application failed'
        self.revision+=1

    def allow_fingers(self,target,enabled):
        request=GetPlanningScene.Request();request.components.components=PlanningSceneComponents.ALLOWED_COLLISION_MATRIX
        matrix=self.call('/get_planning_scene',request).scene.allowed_collision_matrix
        for name in (target,'reuse/link7','reuse/link8'):
            if name not in matrix.entry_names:
                for row in matrix.entry_values:row.enabled.append(False)
                matrix.entry_names.append(name)
                matrix.entry_values.append(AllowedCollisionEntry(enabled=[False]*len(matrix.entry_names)))
        for finger in ('reuse/link7','reuse/link8'):
            a,b=matrix.entry_names.index(target),matrix.entry_names.index(finger)
            matrix.entry_values[a].enabled[b]=enabled;matrix.entry_values[b].enabled[a]=enabled
        change=ApplyPlanningScene.Request();change.scene.is_diff=True;change.scene.robot_state.is_diff=True
        change.scene.allowed_collision_matrix=matrix
        assert self.call('/apply_planning_scene',change).success
        self.revision+=1

    def plan(self,*,joint_goal=None,pose_goal=None):
        request=GetMotionPlan.Request();motion=request.motion_plan_request
        motion.group_name='manipulator_arm';motion.pipeline_id='ompl';motion.planner_id='RRTConnectkConfigDefault'
        motion.num_planning_attempts=1;motion.allowed_planning_time=2.
        motion.max_velocity_scaling_factor=.08;motion.max_acceleration_scaling_factor=.08
        motion.workspace_parameters.header.frame_id='reuse/odom'
        motion.workspace_parameters.min_corner.x=motion.workspace_parameters.min_corner.y=-5.
        motion.workspace_parameters.min_corner.z=-1.
        motion.workspace_parameters.max_corner.x=motion.workspace_parameters.max_corner.y=5.
        motion.workspace_parameters.max_corner.z=3.
        motion.start_state=self.start_state();constraint=Constraints()
        if joint_goal is not None:
            for name,value in zip(JOINTS,joint_goal):
                constraint.joint_constraints.append(JointConstraint(joint_name=name,position=float(value),
                    tolerance_above=.001,tolerance_below=.001,weight=1.))
        elif pose_goal is not None:
            position=PositionConstraint();position.header=pose_goal.header;position.link_name='reuse/tcp'
            bound=SolidPrimitive(type=SolidPrimitive.SPHERE,dimensions=[.001])
            position.constraint_region.primitives=[bound];position.constraint_region.primitive_poses=[pose_goal.pose]
            position.weight=1.
            orientation=OrientationConstraint();orientation.header=pose_goal.header;orientation.link_name='reuse/tcp'
            orientation.orientation=pose_goal.pose.orientation
            orientation.absolute_x_axis_tolerance=orientation.absolute_y_axis_tolerance=orientation.absolute_z_axis_tolerance=.01
            orientation.weight=1.;constraint.position_constraints=[position];constraint.orientation_constraints=[orientation]
        else:raise ValueError('one joint or pose goal required')
        motion.goal_constraints=[constraint]
        scene=self.scene_hash();start=self.joints();revision=self.revision
        response=self.call('/plan_kinematic_path',request).motion_plan_response
        self.records.append(dict(kind='plan',error_code=response.error_code.val,planning_time=response.planning_time,
                                 scene_hash=scene,revision=revision,
                                 trajectory=message_to_ordereddict(response.trajectory)))
        if response.error_code.val!=1:return None
        return dict(trajectory=response.trajectory,start=start,revision=revision,scene_hash=scene)

    def attach_observed_cylinder(self,name,center):
        # Planning representation only, after measured dual-finger contact.
        # The engine's target remains a free body; no weld or position command.
        T=self.tcp();relative=T[:3,:3].T@(np.asarray(center)-T[:3,3])
        cylinder=object_cylinder(name,relative);cylinder.header.frame_id='reuse/tcp'
        cylinder.primitive_poses=[pose(relative,Rotation.from_matrix(T[:3,:3].T))]
        attached=AttachedCollisionObject(link_name='reuse/tcp',object=cylinder,
                                        touch_links=['reuse/link7','reuse/link8'])
        request=ApplyPlanningScene.Request();request.scene.is_diff=True;request.scene.robot_state.is_diff=True
        request.scene.robot_state.attached_collision_objects=[attached]
        # ADD attached geometry moves the same id out of the world itself.
        # An extra world REMOVE is processed afterwards and falsely fails.
        assert self.call('/apply_planning_scene',request).success
        check=GetPlanningScene.Request();check.components.components=(PlanningSceneComponents.WORLD_OBJECT_NAMES|PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
        scene=self.call('/get_planning_scene',check).scene
        assert name not in [obj.id for obj in scene.world.collision_objects]
        held=[obj for obj in scene.robot_state.attached_collision_objects if obj.object.id==name]
        assert len(held)==1 and held[0].link_name=='reuse/tcp','attached scene postcondition failed'
        self.records.append(dict(kind='attach_observed_geometry',id=name,relative_center=relative.tolist(),
                                 physical_attachment=False,world_object_removed=True))
        self.revision+=1

    def cartesian(self,waypoints):
        request=GetCartesianPath.Request();request.header.frame_id='reuse/odom'
        request.start_state=self.start_state();request.group_name='manipulator_arm';request.link_name='reuse/tcp'
        request.waypoints=waypoints;request.max_step=.005;request.jump_threshold=2.
        request.revolute_jump_threshold=.1;request.prismatic_jump_threshold=.005
        request.avoid_collisions=True;request.max_velocity_scaling_factor=.08;request.max_acceleration_scaling_factor=.08
        request.cartesian_speed_limited_link='reuse/tcp';request.max_cartesian_speed=.02
        scene=self.scene_hash();start=self.joints();revision=self.revision
        response=self.call('/compute_cartesian_path',request)
        residual=float('inf')
        trajectory=response.solution
        if trajectory.joint_trajectory.points:
            names=trajectory.joint_trajectory.joint_names;positions=trajectory.joint_trajectory.points[-1].positions
            end=np.array([positions[names.index(j)] for j in JOINTS])
            final=waypoints[-1].position
            residual=float(np.linalg.norm(self.tcp(end)[:3,3]-[final.x,final.y,final.z]))
        self.records.append(dict(kind='cartesian',fraction=response.fraction,error_code=response.error_code.val,
                                 endpoint_error_m=residual,scene_hash=scene,revision=revision,
                                 trajectory=message_to_ordereddict(trajectory)))
        if not cartesian_complete(response.fraction,response.error_code.val,residual):return None
        return dict(trajectory=trajectory,start=start,revision=revision,scene_hash=scene)

    def prepare_execution(self,plan):
        """Prove timing feasibility without mutating or executing the plan."""
        trajectory=plan['trajectory'].joint_trajectory
        points=[dict(time=p.time_from_start.sec+p.time_from_start.nanosec/1e9,positions=list(p.positions),
                     velocities=list(p.velocities),accelerations=list(p.accelerations)) for p in trajectory.points]
        limits=[[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]
        measured=self.joints()
        return self.compute(lambda:normalize_points(tuple(trajectory.joint_names),points,measured,limits))

    def choose_timed_plan(self,plans):
        feasible=[]
        for index,plan in enumerate(plans):
            try:prepared,scale=self.prepare_execution(plan)
            except ValueError as error:
                self.records.append(dict(kind='execution_candidate_rejected',candidate=index,reason=str(error)))
                continue
            duration=prepared[-1]['time']
            self.records.append(dict(kind='execution_candidate_timing',candidate=index,duration_sim_s=duration,scale=scale))
            feasible.append((duration,index))
        return min(feasible)[1] if feasible else None

    def execute(self,plan,cancel_after_sim_s=None):
        if plan is None:raise ValueError('complete valid plan required')
        current=self.snapshot();sample=current['observation']
        assert execution_admission(plan['revision'],self.revision,plan['start'],self.joints(),
            sample['capture_ns'],current['clock_ns'],sample['capture_wall'],__import__('time').monotonic()),'stale plan/state/observation'
        assert plan['scene_hash']==self.scene_hash(),'planning scene changed before execution'
        assert self.node.count_publishers('/planning_scene')==0,'unexpected planning scene writer'
        goal=FollowJointTrajectory.Goal();goal.trajectory=plan['trajectory'].joint_trajectory
        trajectory=goal.trajectory
        prepared,scale=self.prepare_execution(plan)
        for point,updated in zip(trajectory.points,prepared):
            total_ns=round(updated['time']*1e9);point.time_from_start.sec=total_ns//1_000_000_000
            point.time_from_start.nanosec=total_ns%1_000_000_000
            point.velocities=updated['velocities'];point.accelerations=updated['accelerations']
        self.records.append(dict(kind='execution_time_adapter',scale=scale,positions_preserved=True,
                                 boundary_velocity_acceleration_zero=True))
        current=self.snapshot();sample=current['observation']
        assert execution_admission(plan['revision'],self.revision,plan['start'],self.joints(),
            sample['capture_ns'],current['clock_ns'],sample['capture_wall'],__import__('time').monotonic()),'state changed during time adaptation'
        send_start=__import__('time').monotonic()
        sent=self.execution.send_goal_async(goal)
        self.records.append(dict(kind='action_send',points=len(trajectory.points),
                                 wall_s=__import__('time').monotonic()-send_start))
        assert self.until(sent.done,3.)
        handle=sent.result();assert handle.accepted,'MoveIt execution rejected'
        result=handle.get_result_async()
        if cancel_after_sim_s is not None:
            start=current['clock_ns']
            assert self.until(lambda:self.snapshot()['clock_ns']-start>=cancel_after_sim_s*1e9 or result.done(),10.)
            assert not result.done(),'execution finished before cancel injection'
            cancel_wall=__import__('time').monotonic()
            canceled=handle.cancel_goal_async();assert self.until(canceled.done,3.),'native cancel ACK deadline'
            assert canceled.result().goals_canceling,'MoveIt cancel ACK absent'
            self.records.append(dict(kind='cancel_ack',wall_s=__import__('time').monotonic()-cancel_wall))
        assert self.until(result.done,240.),'MoveIt actual execution terminal deadline'
        terminal=result.result()
        self.records.append(dict(kind='execute',status=terminal.status,error_code=terminal.result.error_code,
                                 route='MoveIt_plan_to_native_FollowJointTrajectory'))
        if cancel_after_sim_s is None:assert terminal.status==4 and terminal.result.error_code==0,terminal
        else:assert terminal.status==5,terminal
        return terminal

    def close(self):
        self.compute_worker.shutdown(wait=True,cancel_futures=True)
        self.execution.destroy()
        for client in self.clients.values():self.node.destroy_client(client)
