"""Bound survey work by simulation duration and an independent steady limit."""
import math

SIM_SECONDS=120
WALL_SECONDS=240


class SurveyBudget:
    def __init__(self,*,clock_ns,wall):
        if type(clock_ns) is not int or clock_ns<=0 or not math.isfinite(wall):
            raise ValueError('initialized simulation and steady clocks required')
        self.start_clock=clock_ns
        self.start_wall=wall
        self.last_clock=clock_ns
        self.last_wall=wall

    def record_start(self,port):
        port.event('survey_budget_started',clock_ns=self.start_clock,
                   budget_start_wall=self.start_wall,sim_budget_s=SIM_SECONDS,wall_budget_s=WALL_SECONDS)

    def reason(self,*,clock_ns,wall):
        if (type(clock_ns) is not int or clock_ns<self.last_clock
                or not math.isfinite(wall) or wall<self.last_wall):
            raise ValueError('survey clock invalid or reversed')
        self.last_clock=clock_ns
        self.last_wall=wall
        if clock_ns-self.start_clock>=SIM_SECONDS*1_000_000_000:
            return 'sim_deadline'
        if wall-self.start_wall>=WALL_SECONDS:
            return 'wall_deadline'
        return None
