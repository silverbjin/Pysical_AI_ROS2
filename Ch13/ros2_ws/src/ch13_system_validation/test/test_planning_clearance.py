"""Planning clearance is authoritative scene data, never physical attachment."""
from types import SimpleNamespace
import pytest
from moveit_msgs.msg import PlanningScene,LinkPadding,LinkScale,PlanningSceneComponents
from moveit_msgs.srv import ApplyPlanningScene
from ch13_manipulation_reuse.planning import Planner
from ch13_system_validation.scenarios import get_scenario

class ScenePort:
    def __init__(self,mode='ok'):
        self.scene=PlanningScene();self.revision=0;self.records=[];self.calls=[];self.mode=mode
    def call(self,name,request):
        self.calls.append((name,request))
        if name=='/apply_planning_scene':
            assert request.scene.is_diff and request.scene.robot_state.is_diff
            assert not request.scene.world.collision_objects
            if self.mode=='apply_fail':return SimpleNamespace(success=False)
            self.scene.link_padding=list(request.scene.link_padding)
            if self.mode=='missing':self.scene.link_padding=[]
            if self.mode=='wrong':self.scene.link_padding[0].padding=.01
            return SimpleNamespace(success=True)
        assert name=='/get_planning_scene'
        return SimpleNamespace(scene=self.scene)
    def scene_hash(self):return Planner.scene_hash(self)

@pytest.mark.parametrize('name',['development','level1_floor','level2_obstacles'])
def test_clearance_is_opt_in_to_only_the_under_table_arm(name):
    from ch13_system_validation.planning_clearance import apply_pregrasp_clearance
    port=ScenePort();assert apply_pregrasp_clearance(port,get_scenario(name)) is None
    assert not port.calls and port.revision==0

def test_padding_requires_real_readback_and_records_its_scene_binding():
    from ch13_system_validation.planning_clearance import apply_pregrasp_clearance
    port=ScenePort();before=port.scene_hash()
    result=apply_pregrasp_clearance(port,get_scenario('level3_house'))
    assert result['link_padding_m']=={'reuse/link3':.03}
    assert result['scene_hash']==port.scene_hash()!=before
    assert port.revision==1 and port.records[-1]['kind']=='planning_clearance'
    assert any(req.components.components & PlanningSceneComponents.LINK_PADDING_AND_SCALING for name,req in port.calls if name=='/get_planning_scene')

@pytest.mark.parametrize('mode',['apply_fail','missing','wrong'])
def test_failed_or_unconfirmed_margin_never_admits_planning(mode):
    from ch13_system_validation.planning_clearance import apply_pregrasp_clearance
    with pytest.raises(ValueError):apply_pregrasp_clearance(ScenePort(mode),get_scenario('level3_house'))

def test_scene_hash_tracks_nondefault_padding_and_scaling():
    port=ScenePort();baseline=port.scene_hash()
    port.scene.link_padding=[LinkPadding(link_name='reuse/link3',padding=.03)]
    padded=port.scene_hash();assert padded!=baseline
    port.scene.link_scale=[LinkScale(link_name='reuse/link3',scale=.9)]
    assert port.scene_hash()!=padded

def test_default_padding_and_scale_keep_legacy_scene_hash():
    port=ScenePort();baseline=port.scene_hash()
    port.scene.link_padding=[LinkPadding(link_name='reuse/link3',padding=0.)]
    port.scene.link_scale=[LinkScale(link_name='reuse/link3',scale=1.)]
    assert port.scene_hash()==baseline
