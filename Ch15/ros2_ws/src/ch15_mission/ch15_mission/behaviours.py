import py_trees
class Task(py_trees.behaviour.Behaviour):
    def __init__(self,name,owner):
        super().__init__(name);self.owner=owner
    def initialise(self):self.owner.enter(self.name)
    def update(self):return self.owner.step(self.name)
    def terminate(self,new_status):
        if new_status==py_trees.common.Status.INVALID:self.owner.interrupt(self.name)
class PickObjectBehaviour(py_trees.behaviour.Behaviour):
    def __init__(self,name,supervisor,target_provider):
        super().__init__(name);self.supervisor=supervisor;self.target_provider=target_provider;self.request_id=None
    def initialise(self):self.request_id=None
    def update(self):
        S=py_trees.common.Status
        if self.request_id is None:
            goal=self.target_provider()
            if goal is None:return S.FAILURE
            if not self.supervisor.ready_for_goal():return S.FAILURE
            self.request_id=self.supervisor.send(goal)
        result=self.supervisor.poll(self.request_id)
        return S.SUCCESS if result=='SUCCEEDED_VERIFIED' else S.FAILURE if result in ('FAILED','REJECTED','CANCELED','ABORTED') else S.RUNNING
    def terminate(self,new_status):
        if self.request_id is not None and new_status==py_trees.common.Status.INVALID:self.supervisor.request_cancel(self.request_id)
