"""Planning-only detachment after physical release, with measured world geometry."""
import math
from scipy.spatial.transform import Rotation
from moveit_msgs.msg import AttachedCollisionObject,CollisionObject,PlanningSceneComponents
from moveit_msgs.srv import ApplyPlanningScene,GetPlanningScene
from ch13_manipulation_reuse.planning import object_cylinder
from ch13_mission_orchestration.session import admit_observation


def detach_released_cylinder(planner,observation,*,clock_ns,wall,released_ns):
    sample=admit_observation(observation,clock_ns,wall)
    if type(released_ns) is not int or released_ns<=0 or sample['capture_ns']<=released_ns:
        raise ValueError('new original observation after physical release required')
    change=ApplyPlanningScene.Request();change.scene.is_diff=True;change.scene.robot_state.is_diff=True
    # ID-only REMOVE follows the installed MoveIt contract. A wrong nonempty
    # parent is rejected inside a diff even when its outer service reply is true.
    removed=AttachedCollisionObject();removed.object.id='pick_target';removed.object.operation=CollisionObject.REMOVE
    change.scene.robot_state.attached_collision_objects=[removed]
    change.scene.world.collision_objects=[object_cylinder('pick_target',sample['point'])]
    if not planner.call('/apply_planning_scene',change).success:raise ValueError('detach scene application failed')
    check=GetPlanningScene.Request();check.components.components=(PlanningSceneComponents.WORLD_OBJECT_GEOMETRY|
        PlanningSceneComponents.WORLD_OBJECT_NAMES|PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
    scene=planner.call('/get_planning_scene',check).scene
    attached=[body for body in scene.robot_state.attached_collision_objects if body.object.id=='pick_target']
    world=[body for body in scene.world.collision_objects if body.id=='pick_target']
    if attached or len(world)!=1:raise ValueError('detach postcondition: owned object must exist only in world')
    body=world[0]
    if len(body.primitive_poses)!=1:raise ValueError('detach postcondition: world geometry missing')
    origin=body.pose;shape=body.primitive_poses[0].position;q=origin.orientation
    point=Rotation.from_quat([q.x,q.y,q.z,q.w]).apply([shape.x,shape.y,shape.z])+[origin.position.x,origin.position.y,origin.position.z]
    if math.dist(point,sample['point'])>1e-6:raise ValueError('detach postcondition: world pose differs from observation')
    planner.revision+=1
    planner.records.append(dict(kind='detach_observed_geometry',id='pick_target',source_capture_ns=sample['capture_ns'],
        released_ns=released_ns,world_center=point.tolist(),attached_removed=True,physical_attachment=False))
