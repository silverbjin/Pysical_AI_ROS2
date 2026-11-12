"""Book exercise boundaries, distinct from full pick/return/place acceptance."""


def configure_tasks(mission, exercise):
    from ch13_mission_orchestration.tree import Task
    main = mission.root.children[-1]
    if exercise == 'basic':
        for child in list(main.children):
            if isinstance(child, Task) and child.task == 'pick':
                main.remove_child(child)
    elif exercise == 'full':
        finish = main.children[-1]
        main.remove_child(finish)
        main.add_children([Task('return', mission), Task('place', mission), finish])
    else:
        raise ValueError('unknown exercise: '+str(exercise))


def assess_basic(bt, navigation, engine, *, recording_complete, telemetry_joined,
                 world_pass, manipulation_artifacts):
    port = bt.get('port', {})
    completed = port.get('completed', {})
    forbidden = {'pick', 'return', 'place'}
    goals = bt.get('goals', {})
    handoff = navigation.get('manipulation_handoff', {})
    pids = navigation.get('owned_launch_pids', [])
    checks = dict(
        motion_observation=all(k in completed for k in ('navigate', 'find', 'finish')),
        terminal=bt.get('terminal') == 'SUCCESS' and navigation.get('result') == 'PASS',
        no_manipulation=not forbidden.intersection(port.get('requested', [])) and
            not forbidden.intersection(completed) and not manipulation_artifacts and
            handoff.get('exercise') == 'basic' and handoff.get('manipulation_executed') is False,
        worker=bt.get('worker_joined') is True and port.get('closed') is True and
            port.get('exit_code') == 0 and not port.get('error'),
        goals=goals.get('pending') == 0 and goals.get('errors') == [],
        engine=engine.get('normal_shutdown_requested') is True and
            engine.get('rx_joined') is True and engine.get('upstream_threads_joined') is True and
            not engine.get('final_fault'),
        children=bool(pids) and navigation.get('clean_launch_exits') == len(pids) and
            navigation.get('remaining_launch_pids') == [] and navigation.get('launch_exit_code') == 0,
        recording=recording_complete is True, telemetry=telemetry_joined is True,
        world=world_pass is True)
    return dict(result='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                scope='basic_navigation_observation_only', full_mission_success=False)
