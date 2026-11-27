"""G03 base contract; no automatic recovery or retry until G08."""
def reset_allowed(active,unresolved,stopped,fresh_ready,latched):
    return not active and not unresolved and stopped and fresh_ready and not latched
def outcome(root_success,normal_verified,safety_requested):
    if safety_requested:return 'ABORTED'
    return 'COMPLETED' if root_success and normal_verified else 'ERROR'

class RetryBudget:
    """Bounded one-operation retries. Preparation failures consume attempts.
    No actual goal is sent by this policy; mission adapter must supply witnesses.
    """
    def __init__(self,limit=3):
        if type(limit) is not int or not 1<=limit<=3:
            raise ValueError('retry limit must be 1..3')
        self.limit=limit
        self.attempts=0
        self.active=False
        self.prepared=False
        self.finished=False
        self.aborted=False

    def begin(self,*,safe,previous_terminal):
        if self.active or self.finished or self.aborted:
            return False
        if safe is not True or previous_terminal is not True or self.attempts>=self.limit:
            self.aborted=True
            return False
        self.attempts+=1
        self.active=True
        self.prepared=False
        return True

    def prepare(self,*,safe,settled,fresh,previous_terminal):
        if not self.active or self.prepared:
            return False
        if safe is not True or previous_terminal is not True:
            self.active=False
            self.aborted=True
            return False
        if settled is not True or fresh is not True:
            self.active=False
            self.aborted=self.attempts>=self.limit
            return False
        self.prepared=True
        return True

    def resolve(self,*,safe,terminal,original_verified,recovery_success=False):
        if not self.active or not self.prepared:
            raise RuntimeError('no prepared attempt')
        self.active=False
        self.prepared=False
        if safe is not True or terminal is not True:
            self.aborted=True
        elif original_verified is True:
            self.finished=True
        elif self.attempts>=self.limit:
            self.aborted=True
        # recovery_success alone never marks original task success
        return 'SUCCESS' if self.finished else 'ABORT' if self.aborted else 'RETRY'
