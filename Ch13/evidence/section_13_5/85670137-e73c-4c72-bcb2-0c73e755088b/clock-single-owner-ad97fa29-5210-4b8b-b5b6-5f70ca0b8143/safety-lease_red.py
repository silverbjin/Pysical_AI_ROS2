"""Scoped temporary lease for the explicitly approved shared-clock comparison."""
class ClockLease:
    def __init__(self, ops, save):
        self.ops,self.save=ops,save
        self.record={'restoration_pending':False,'restored':False,'errors':[]}
    def begin(self):
        return self.record
    def close(self):
        return False
