"""Scoped planning contact for placing an object onto its receiving support."""
import copy
from moveit_msgs.msg import AllowedCollisionEntry,PlanningSceneComponents
from moveit_msgs.srv import GetPlanningScene,ApplyPlanningScene


def permit_pair(matrix,first,second,enabled):
    result=copy.deepcopy(matrix)
    for name in (first,second):
        if name not in result.entry_names:
            for row in result.entry_values:row.enabled.append(False)
            result.entry_names.append(name)
            result.entry_values.append(AllowedCollisionEntry(enabled=[False]*len(result.entry_names)))
    a,b=result.entry_names.index(first),result.entry_names.index(second)
    result.entry_values[a].enabled[b]=enabled;result.entry_values[b].enabled[a]=enabled
    return result


def receiving_contact(planner,enabled,*,support_name='reuse_receiving_support'):
    request=GetPlanningScene.Request();request.components.components=PlanningSceneComponents.ALLOWED_COLLISION_MATRIX
    matrix=planner.call('/get_planning_scene',request).scene.allowed_collision_matrix
    change=ApplyPlanningScene.Request();change.scene.is_diff=True;change.scene.robot_state.is_diff=True
    change.scene.allowed_collision_matrix=permit_pair(matrix,'pick_target',support_name,enabled)
    assert planner.call('/apply_planning_scene',change).success,'support collision diff rejected'
    planner.revision+=1
    planner.records.append(dict(kind='receiving_support_contact',support_name=support_name,enabled=enabled,physical_attachment=False))
