"""Level 3 planning margin confirmed by the authoritative MoveIt scene."""
import math
from moveit_msgs.msg import LinkPadding, PlanningSceneComponents
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene


def apply_pregrasp_clearance(planner, scenario):
    if scenario.name != 'level3_house':
        return None
    link = 'reuse/link3'
    margin = .03
    request = ApplyPlanningScene.Request()
    request.scene.is_diff = True
    request.scene.robot_state.is_diff = True
    request.scene.link_padding = [LinkPadding(link_name=link, padding=margin)]
    if not planner.call('/apply_planning_scene', request).success:
        raise ValueError('planning clearance application failed')
    query = GetPlanningScene.Request()
    query.components.components = PlanningSceneComponents.LINK_PADDING_AND_SCALING
    scene = planner.call('/get_planning_scene', query).scene
    values = [row.padding for row in scene.link_padding if row.link_name == link]
    if len(values) != 1 or not math.isclose(values[0], margin, rel_tol=0., abs_tol=1e-9):
        raise ValueError('planning clearance readback mismatch')
    planner.revision += 1
    record = dict(kind='planning_clearance', link_padding_m={link: margin},
                  scene_revision=planner.revision, scene_hash=planner.scene_hash())
    planner.records.append(record)
    return record
