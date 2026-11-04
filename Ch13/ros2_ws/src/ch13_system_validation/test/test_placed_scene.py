"""A true ApplyPlanningScene reply must not hide an attached-body removal failure."""
import copy
from types import SimpleNamespace
import numpy as np
import pytest
from moveit_msgs.msg import AttachedCollisionObject,CollisionObject,PlanningScene
from ch13_system_validation.placed_scene import detach_released_cylinder


def observation():
    return dict(point=[-.7986,-.0174,.5399],capture_ns=1_100_000_000,capture_wall=10.1,
        first_receipt_wall=10.11,tf_stamp_ns=1_090_000_000,source_gids={'rgb':'stable'},
        rgb_sha256='a'*64,source='actual_Renderer_RGBD_known_upright_cylinder_fit',cylinder_fit={})


class SceneServer:
    def __init__(self,ignore_removal=False):
        self.revision=0;self.records=[];self.calls=[];self.ignore=ignore_removal
        self.attached=True;self.world=[]
    def call(self,name,request):
        self.calls.append((name,copy.deepcopy(request)))
        if name=='/apply_planning_scene':
            change=request.scene.robot_state.attached_collision_objects[0]
            assert change.object.id=='pick_target' and change.object.operation==CollisionObject.REMOVE
            # MoveIt 2.12.4 rejects a wrong parent even if the outer diff reply is true.
            if change.link_name in ('','reuse/tcp') and not self.ignore:self.attached=False
            self.world=copy.deepcopy(request.scene.world.collision_objects)
            return SimpleNamespace(success=True)
        scene=PlanningScene();scene.world.collision_objects=self.world
        if self.attached:
            body=AttachedCollisionObject(link_name='reuse/tcp');body.object.id='pick_target'
            scene.robot_state.attached_collision_objects=[body]
        return SimpleNamespace(scene=scene)


def test_detach_by_id_uses_fresh_measured_placement_and_checks_scene_readback():
    server=SceneServer();sample=observation()
    detach_released_cylinder(server,sample,clock_ns=1_200_000_000,wall=10.2,released_ns=1_000_000_000)
    assert not server.attached and server.revision==1
    removed=server.calls[0][1].scene.robot_state.attached_collision_objects[0]
    assert removed.link_name==''
    point=server.world[0].primitive_poses[0].position
    np.testing.assert_allclose([point.x,point.y,point.z],sample['point'])


def test_outer_apply_success_with_still_attached_body_is_a_hard_failure():
    server=SceneServer(ignore_removal=True)
    with pytest.raises(ValueError,match='detach postcondition'):
        detach_released_cylinder(server,observation(),clock_ns=1_200_000_000,wall=10.2,released_ns=1_000_000_000)
    assert server.revision==0


def test_pre_release_or_expired_observation_cannot_move_the_world_collision_object():
    for released,wall in ((1_150_000_000,10.2),(1_000_000_000,10.5)):
        server=SceneServer()
        with pytest.raises(ValueError):
            detach_released_cylinder(server,observation(),clock_ns=1_200_000_000,wall=wall,released_ns=released)
        assert not server.calls
