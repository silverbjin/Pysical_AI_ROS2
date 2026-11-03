"""Only the upstream loop's pacing clock is replaced, never physics/policy time."""
import math,time
class SteadyScheduler:
 def __init__(self,dt,monotonic=time.monotonic,wall=time.time,sleeper=time.sleep):
  self.dt=dt;self.monotonic=monotonic;self.wall=wall;self.sleeper=sleeper;self.last=None;self.events=[];self.max_sleep=0.
 def time(self):
  steady=self.monotonic();absolute=self.wall()
  if self.last is not None:
   difference=(absolute-self.last[1])-(steady-self.last[0])
   if abs(difference)>.1 and len(self.events)<20:self.events.append({'steady':steady,'absolute_clock_delta_error_s':difference})
  self.last=(steady,absolute);return steady
 def sleep(self,duration):
  if not math.isfinite(duration) or duration<0 or duration>self.dt+1e-6:raise ValueError('upstream sleep exceeds physics period')
  self.max_sleep=max(self.max_sleep,duration);self.sleeper(duration)
 def summary(self):return {'clock':'CLOCK_MONOTONIC for upstream run only','max_sleep_requested_s':self.max_sleep,'physics_dt_s':self.dt,'absolute_clock_events':self.events}
