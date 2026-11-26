"""Chapter 15.1 pure mission contract; no ROS commands or physical claims."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from geometry_msgs.msg import PoseStamped

class RobotState(Enum):
    IDLE=auto(); NAVIGATING=auto(); SEARCHING=auto(); APPROACHING=auto()
    MANIPULATING=auto(); RETURNING=auto(); PLACING=auto(); COMPLETED=auto()
    ERROR=auto(); ABORTED=auto()

class ErrorCode(Enum):
    NONE=0; NAVIGATION_STUCK=1; OBJECT_NOT_FOUND=2; GRASP_FAILED=3
    LOW_BATTERY=4; SENSOR_TIMEOUT=5; STALE_TARGET=6
    CANCEL_UNCONFIRMED=7; CLOCK_INVALID=8

PROFILES=('mock','physical_basic','physical_full')
TERMINALS=(RobotState.COMPLETED,RobotState.ERROR,RobotState.ABORTED)
STAGES={'navigate':RobotState.NAVIGATING,'detect':RobotState.SEARCHING,
        'approach_stand':RobotState.APPROACHING,'pick_retract':RobotState.MANIPULATING,
        'return_home':RobotState.RETURNING,'place':RobotState.PLACING,'verify_finish':None}

def steps_for(profile):
    if profile=='mock': return tuple(STAGES)
    if profile=='physical_basic': return ('navigate','detect','approach_stand','verify_finish')
    raise ValueError('PHYSICAL_FULL_BLOCKED' if profile=='physical_full' else 'unknown profile')

@dataclass
class MissionContext:
    mission_id: str
    profile: str='mock'
    target_object_class: str='red_cube'
    target_location: PoseStamped | None=None
    is_object_grasped: bool=False
    grasp_source: str='UNKNOWN'
    virtual_battery_pct: float=100.0
    state: RobotState=RobotState.IDLE
    error_code: ErrorCode=ErrorCode.NONE
    full_mission_success: bool=False
    def __post_init__(self):
        steps_for(self.profile)
        if not isinstance(self.mission_id,str) or not self.mission_id.strip(): raise ValueError('mission_id')
        if type(self.virtual_battery_pct) not in (int,float) or not math.isfinite(self.virtual_battery_pct) or not 0<=self.virtual_battery_pct<=100: raise ValueError('battery')
        if self.full_mission_success or self.is_object_grasped or self.grasp_source!='UNKNOWN' or self.state!=RobotState.IDLE or self.error_code!=ErrorCode.NONE: raise ValueError('initial state must be clean')
        if self.profile=='physical_basic': self.target_object_class='upright_cylinder'
        elif self.target_object_class!='red_cube': raise ValueError('mock target class')

class MissionRegistry:
    """Pure ordered-transition oracle. Readiness is an explicit prerequisite."""
    def __init__(self): self.seen=set(); self.active=None; self.index=0; self.ready=False
    def start(self, mission_id, profile):
        if self.active is not None or mission_id in self.seen: raise ValueError('active or reused mission')
        context=MissionContext(mission_id,profile)
        self.seen.add(mission_id); self.active=context; self.index=0; self.ready=False
        return context
    def _owned(self,mission_id):
        if self.active is None or self.active.mission_id!=mission_id: raise ValueError('no matching active mission')
        return self.active
    def mark_ready(self,mission_id):
        self._owned(mission_id); self.ready=True
    def advance(self,mission_id,step):
        c=self._owned(mission_id); expected=steps_for(c.profile)
        if not self.ready or self.index>=len(expected) or expected[self.index]!=step: raise ValueError('unexpected or unready step')
        if STAGES[step] is not None: c.state=STAGES[step]
        self.index+=1
    def finish(self,mission_id,state):
        c=self._owned(mission_id)
        if state not in TERMINALS or (state==RobotState.COMPLETED and self.index!=len(steps_for(c.profile))): raise ValueError('invalid terminal')
        c.state=state; self.active=None; self.ready=False

FAULTS={f'F{i:02d}' for i in range(1,11)}
def validate_scenario(row):
    keys={'fault_id','profile','trigger','seed','expected_mission_terminal','required_witness','retry_budget'}
    if not isinstance(row,dict) or set(row)!=keys: raise ValueError('scenario schema')
    if row['fault_id'] not in FAULTS|{'NORMAL'} or row['profile']!='mock': raise ValueError('scenario profile/id')
    if type(row['seed']) is not int or row['seed']<0 or type(row['retry_budget']) is not int or not 0<=row['retry_budget']<=3: raise ValueError('scenario budget')
    if not isinstance(row['trigger'],str) or not row['trigger'].strip() or not isinstance(row['required_witness'],list) or not row['required_witness'] or any(not isinstance(x,str) or not x.strip() for x in row['required_witness']): raise ValueError('scenario witness')
    if row['expected_mission_terminal'] not in ('COMPLETED','ABORTED','ERROR','COMPLETED_OR_ABORTED'): raise ValueError('scenario terminal')
    if row['fault_id']=='NORMAL' and row['expected_mission_terminal']!='COMPLETED': raise ValueError('normal terminal')
    return row
