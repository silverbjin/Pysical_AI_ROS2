"""Deterministic simulated behaviours, never connected to robot endpoints."""
from .tasks import TaskPort
from .tree import Mission


def run_mock(case):
    if case not in ('normal','low_battery','fallen','not_found'):raise ValueError(case)
    port=TaskPort();mission=Mission(port,profile='mock');mission.fallen=case=='fallen'
    ages={}
    for tick in range(100):
        if case=='low_battery' and tick==2:mission.battery=10.
        mission.tick()
        data=port.snapshot()
        if data['cancel_reason']:port.progress(stopped=True)
        for task in data['requested']:
            if task in data['completed']:continue
            if data['cancel_reason'] and task!='charge':continue
            ages[task]=ages.get(task,0)+1
            if ages[task]<4:continue
            if task=='find' and case=='not_found':port.fail('object_not_found');port.close(1)
            else:port.complete(task,dict(simulated=True,task=task))
        if mission.terminal:break
    data=port.snapshot()
    return dict(profile='mock',case=case,terminal=mission.terminal,requested=data['requested'],
                ticks=mission.ticks,events=data['events'],simulated=True)
