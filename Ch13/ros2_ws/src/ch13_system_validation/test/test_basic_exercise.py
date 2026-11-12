import copy
import importlib

import pytest


def module():
    return importlib.import_module('ch13_system_validation.basic_exercise')


def evidence():
    bt = dict(terminal='SUCCESS', worker_joined=True,
        port=dict(closed=True, exit_code=0, requested=['navigate','find','finish'],
                  completed={k:{} for k in ('navigate','find','finish')}),
        goals=dict(pending=0, errors=[]))
    nav = dict(result='PASS', owned_launch_pids=[1,2], clean_launch_exits=2,
               remaining_launch_pids=[], launch_exit_code=0,
               manipulation_handoff=dict(exercise='basic', manipulation_executed=False))
    engine = dict(normal_shutdown_requested=True, rx_joined=True,
                  upstream_threads_joined=True, final_fault='')
    return bt,nav,engine


def test_basic_pass_is_scoped_to_observation_and_clean_shutdown():
    bt,nav,engine = evidence()
    result = module().assess_basic(bt,nav,engine,recording_complete=True,
        telemetry_joined=True,world_pass=True,manipulation_artifacts=False)
    assert result['result'] == 'PASS'
    assert result['scope'] == 'basic_navigation_observation_only'
    assert result['full_mission_success'] is False


@pytest.mark.parametrize('fault', ['pick','place','not_found','worker','process',
    'thread','bag','world','artifact','goal'])
def test_basic_does_not_hide_failed_motion_or_incomplete_cleanup(fault):
    bt,nav,engine = evidence()
    kwargs=dict(recording_complete=True,telemetry_joined=True,world_pass=True,
                manipulation_artifacts=False)
    if fault in ('pick','place'): bt['port']['requested'].append(fault)
    if fault=='not_found': del bt['port']['completed']['find']
    if fault=='worker': bt['worker_joined']=False
    if fault=='process': nav['remaining_launch_pids']=[2]
    if fault=='thread': engine['rx_joined']=False
    if fault=='bag': kwargs['recording_complete']=False
    if fault=='world': kwargs['world_pass']=False
    if fault=='artifact': kwargs['manipulation_artifacts']=True
    if fault=='goal': bt['goals']['pending']=1
    assert module().assess_basic(bt,nav,engine,**kwargs)['result']=='FAIL'


def test_basic_tree_never_requests_pick_return_or_place_and_full_tree_is_preserved():
    from ch13_mission_orchestration.tree import Mission
    from ch13_mission_orchestration.tasks import TaskPort,STEPS
    port=TaskPort(STEPS+('place',));mission=Mission(port)
    module().configure_tasks(mission,'basic')
    for step in ('navigate','find','finish'):
        mission.tick()
        assert port.snapshot()['requested'][-1]==step
        port.complete(step,{})
    mission.tick()
    assert mission.terminal=='SUCCESS'
    assert port.snapshot()['requested']==['navigate','find','finish']
    full=Mission(TaskPort(STEPS+('place',)))
    module().configure_tasks(full,'full')
    tasks=[c.task for c in full.root.children[-1].children if hasattr(c,'task')]
    assert tasks==['navigate','find','pick','return','place','finish']


def test_basic_failure_latches_and_does_not_request_more_work():
    from ch13_mission_orchestration.tree import Mission
    from ch13_mission_orchestration.tasks import TaskPort
    port=TaskPort();mission=Mission(port);module().configure_tasks(mission,'basic')
    mission.tick();port.fail('sensor fault');port.close(1);mission.tick()
    assert mission.terminal=='FAILURE'
    before=copy.deepcopy(port.snapshot()['requested']);mission.tick()
    assert port.snapshot()['requested']==before==['navigate']
