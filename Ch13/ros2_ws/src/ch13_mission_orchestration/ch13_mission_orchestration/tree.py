"""Nonblocking BT leaves; action ownership outlives leaf invalidation."""
import uuid
import py_trees as pt

S=pt.common.Status


class Check(pt.behaviour.Behaviour):
    def __init__(self,name,predicate):super().__init__(name);self.predicate=predicate
    def update(self):return S.SUCCESS if self.predicate() else S.FAILURE


class Task(pt.behaviour.Behaviour):
    def __init__(self,name,mission):super().__init__(name);self.task=name;self.mission=mission
    def initialise(self):self.mission.port.submit(self.task)
    def update(self):
        data=self.mission.port.snapshot()
        if data['error']:return S.FAILURE
        if self.task in data['completed']:
            if self.task=='find':self.mission.bb.target_pose=data['completed'][self.task]
            return S.SUCCESS
        if data['closed']:return S.FAILURE
        return S.RUNNING
    def terminate(self,new_status):
        if new_status==S.INVALID and self.status==S.RUNNING:self.mission.port.cancel('preempted')


class CancelAndSettle(pt.behaviour.Behaviour):
    def __init__(self,mission):super().__init__('Cancel and settle');self.mission=mission
    def update(self):
        m=self.mission;m.port.cancel(m.stop_reason or 'user_cancel')
        data=m.port.snapshot()
        if m.profile=='mock' and data['progress'].get('stopped'):return S.SUCCESS
        if data['closed']:
            m.terminal='ABORTED' if data['exit_code']==0 and not data['error'] else 'FAILURE'
            return S.SUCCESS
        return S.RUNNING


class MockRecover(Task):
    def update(self):
        result=super().update()
        if result==S.SUCCESS:
            self.mission.fallen=False
            return S.FAILURE  # fall through to mission after the simulated recovery
        return result


class Abort(pt.behaviour.Behaviour):
    def __init__(self,mission):super().__init__('Latch abort');self.mission=mission
    def update(self):self.mission.terminal='ABORTED';return S.SUCCESS


class Mission:
    def __init__(self,port,profile='actual'):
        self.port=port;self.profile=profile;self.battery=100.;self.fallen=False
        self.stop_reason='';self.terminal=None;self.ticks=[]
        self.bb=pt.blackboard.Client(name='mission',namespace='/mission_'+uuid.uuid4().hex)
        for key in ('target_pose','profile','terminal'):
            self.bb.register_key(key=key,access=pt.common.Access.WRITE)
        self.bb.profile=profile;self.bb.target_pose=None;self.bb.terminal=None
        self.root=pt.composites.Selector('Mission priority',memory=False)
        stop=pt.composites.Sequence('Safety stop',memory=True)
        stop.add_children([Check('Stop required',self.stop_required),CancelAndSettle(self)])
        if profile=='mock':stop.add_children([Task('charge',self),Abort(self)])
        main=pt.composites.Sequence('Fetch',memory=True)
        main.add_children([Check('Battery above 20%',lambda:self.battery>20),
                           Task('navigate',self),Task('find',self),Task('pick',self)])
        if profile=='mock':main.add_child(Task('return',self))
        main.add_child(Task('finish',self))
        self.root.add_child(stop)
        if profile=='mock':
            recovery=pt.composites.Sequence('Recovery',memory=False)
            recovery.add_children([Check('Fallen',lambda:self.fallen),MockRecover('recover',self)])
            self.root.add_child(recovery)
        self.root.add_child(main)

    def stop_required(self):
        if self.stop_reason:return True
        data=self.port.snapshot()
        if data['cancel_reason']:self.stop_reason=data['cancel_reason']
        elif self.battery<=20:self.stop_reason='low_battery'
        elif data['error']:self.stop_reason='worker_error'
        return bool(self.stop_reason)

    def tick(self,tree=None):
        if self.terminal:return
        if tree is None:self.root.tick_once()
        else:tree.tick()
        if self.root.status==S.SUCCESS and not self.stop_reason:self.terminal='SUCCESS'
        elif self.root.status==S.FAILURE:self.terminal='FAILURE';self.port.cancel('mission_failure')
        self.bb.terminal=self.terminal
        self.ticks.append(dict(tick=len(self.ticks),profile=self.profile,root=self.root.status.name,
            nodes={n.name:n.status.name for n in self.root.iterate()},terminal=self.terminal,
            target_pose=self.bb.target_pose,battery=self.battery))
