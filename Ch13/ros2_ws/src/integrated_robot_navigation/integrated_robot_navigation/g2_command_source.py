"""Owned G2 velocity fixture, not Nav2/PPO and never a final motor publisher."""
from collections import deque
import json
import math
from pathlib import Path
import threading
import time

from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from geometry_msgs.msg import Twist
from integrated_robot_interfaces.msg import MotionState
from .carry_profile import _validate_limits
from .dispatch_node import NavigationNode


def assess_command_trace(rows,limits):
    """Check every producer record, including the separate immediate stop."""
    count=0;previous=None;stopped=False
    try:
        for index,row in enumerate(rows):
            raw,smooth=row['raw'],row['smoothed'];now=row['wall_ns']
            if (len(raw)!=2 or len(smooth)!=2 or not all(math.isfinite(v) for v in (*raw,*smooth))
                    or type(now) is not int or any(abs(v)>bound for values in (raw,smooth)
                        for v,bound in zip(values,(limits['max_vx'],limits['max_wz'])))):
                return dict(passed=False,reason='invalid command or bounds')
            if row['event']=='stop_zero':
                if index!=len(rows)-1 or any((*raw,*smooth)):return dict(passed=False,reason='nonfinal stop')
                stopped=True;continue
            if row['event']!='publish':return dict(passed=False,reason='unknown command event')
            dt=.02 if previous is None else (now-previous['wall_ns'])/1e9
            if dt<.02:return dict(passed=False,reason='command period')
            old=(0.,0.) if previous is None else previous['smoothed']
            if any(abs(v-p)>accel*dt+1e-12 for v,p,accel in zip(smooth,old,
                    (limits['max_accel_x'],limits['max_accel_wz']))):
                return dict(passed=False,reason='command acceleration')
            previous=row;count+=1
        return dict(passed=count>=2 and stopped,normal_publications=count,final_stop=stopped,
            scope='test_commands_not_native_motion')
    except (KeyError,ValueError,TypeError,OverflowError):return dict(passed=False,reason='command schema')


class G2CommandSource(NavigationNode):
    def __init__(self,limits,*,trace_path=None,**kwargs):
        _validate_limits(limits)
        super().__init__('g2_native_commands',**kwargs)
        self.limits=dict(limits);self.lock=threading.RLock()
        self.target=(0.,0.);self.smoothed=(0.,0.)
        self.closing=False;self.reason='';self.count=0
        self.history=deque(maxlen=512);self.last_publish=time.monotonic_ns()
        self.trace=Path(trace_path).open('x') if trace_path is not None else None
        self.raw=self.create_publisher(Twist,'/navigation/cmd_vel_raw',10)
        self.smooth=self.create_publisher(Twist,'/navigation/cmd_vel_smoothed',10)
        for role in ('guard','crawl'):
            self.create_subscription(MotionState,'/navigation/'+role+'_state',self._fault,10)
        self.timer=self.create_timer(.02,self._tick,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def set_target(self,vx,wz):
        with self.lock:
            if self.closing:raise RuntimeError('G2 command source is permanently closed')
            try:
                values=float(vx),float(wz)
                if (not all(math.isfinite(v) for v in values) or abs(values[0])>self.limits['max_vx']
                        or abs(values[1])>self.limits['max_wz']):raise ValueError('command bounds')
            except (ValueError,TypeError,OverflowError) as error:
                self.stop('invalid_target')
                raise ValueError('finite bounded G2 target required') from error
            self.target=values

    def _publish(self,raw,smoothed,now,*,event='publish'):
        for publisher,values in ((self.raw,raw),(self.smooth,smoothed)):
            message=Twist();message.linear.x=values[0];message.angular.z=values[1]
            publisher.publish(message)
        row=dict(event=event,wall_ns=now,raw=raw,smoothed=smoothed)
        self.count+=1;self.history.append(row)
        if self.trace is not None:
            self.trace.write(json.dumps(row,allow_nan=False)+'\n');self.trace.flush()

    def _tick(self):
        with self.lock:
            if self.closing:return
            now=time.monotonic_ns();elapsed=(now-self.last_publish)/1e9
            if elapsed<.02:return # strict upper command rate; late callbacks never catch up
            dt=min(.02,elapsed)
            values=[]
            for old,target,accel in zip(self.smoothed,self.target,
                    (self.limits['max_accel_x'],self.limits['max_accel_wz'])):
                values.append(old+max(-accel*dt,min(accel*dt,target-old)))
            self.smoothed=tuple(values);self.last_publish=now
            self._publish(self.target,self.smoothed,now)

    def _fault(self,message):
        if message.state=='FAULT' or message.fault_reason:
            self.stop('runtime_fault:'+message.fault_reason)

    def stop(self,reason='shutdown'):
        with self.lock:
            if self.closing:return
            self.closing=True;self.reason=reason;self.target=self.smoothed=(0.,0.)
            self.timer.cancel()
            # Immediate final zero is a stop, not a rate-limited moving command.
            self._publish((0.,0.),(0.,0.),time.monotonic_ns(),event='stop_zero')

    def report(self):
        with self.lock:return dict(closing=self.closing,reason=self.reason,count=self.count,
            source='G2_fixture_not_Nav2_or_native_odometry',publications=list(self.history))

    def destroy_node(self):
        self.stop()
        if self.trace is not None:self.trace.close();self.trace=None
        return super().destroy_node()
