"""Measured crawl sequence; command integration is never an arrival estimate."""
import math
from .projection import body_rotation,project_body
from .samples import Sample,sample_valid


def movement_snapshot(frame,ros_ns,wall_ns,limits):
    try:
        body=Sample(**frame['samples']['body']);contacts=Sample(**frame['samples']['contacts'])
        for name,value in (('body',body),('contacts',contacts)):
            valid,reason=sample_valid(value,ros_ns,wall_ns,0,max_age_ns=int(limits['sensor_max_age_s']*1e9))
            if not valid:raise ValueError('native movement '+name+':'+reason)
        planar=project_body(body).data;_,angles=body_rotation(body.data)
        return dict(pose=(*body.data['position'][:2],angles[2]),capture_ns=min(body.stamp_ns,contacts.stamp_ns),
            wall_ns=frame.get('wall_ns',min(body.received_ns,contacts.received_ns)),
            motion_state=frame['crawl'].get('state'),
            stage=frame.get('stage','stand'),stopped=frame['crawl'].get('stopped') is True,
            linear_speed=math.hypot(*planar['linear_velocity'][:2]),yaw_speed=abs(planar['angular_velocity'][2]),
            touching=tuple(contacts.data['touching']))
    except (KeyError,TypeError,IndexError) as error:raise ValueError('missing native movement snapshot') from error


class MeasuredSettle:
    def __init__(self,limits):self.limits=limits;self.start=None;self.last=None
    def update(self,row):
        token=row['capture_ns'],row['wall_ns']
        if self.last is not None and (token[0]<self.last[0] or token[1]<self.last[1]):
            raise ValueError('native settle clock rollback')
        previous=self.last;self.last=token
        healthy=(row['stopped'] and len(row['touching'])==4 and all(row['touching'])
            and row['linear_speed']<=self.limits['stopped_v_mps'] and row['yaw_speed']<=self.limits['stopped_wz_rps'])
        if not healthy:self.start=None;return False
        if previous is not None and token[0]==previous[0]:return False
        if self.start is None:self.start=token
        duration=int(self.limits['settle_s']*1e9)
        return token[0]-self.start[0]>=duration and token[1]-self.start[1]>=duration


def _reached(start,current,phase):
    dx,dy=current[0]-start[0],current[1]-start[1]
    if phase in ('forward','reverse'):
        along=math.cos(start[2])*dx+math.sin(start[2])*dy
        return along>=.4 if phase=='forward' else along<=-.1
    yaw=math.atan2(math.sin(current[2]-start[2]),math.cos(current[2]-start[2]))
    return yaw>=.3 if phase=='left' else yaw<=-.3


def run_sequence(scenario,*,snapshot,source,mode,wait,set_stage,limits):
    if scenario not in ('crawl-cycle','crawl-reverse'):raise ValueError('unknown G2 sequence')
    phases={}
    for name in (('forward','left','right') if scenario=='crawl-cycle' else ('reverse',)):
        set_stage(name);start=snapshot()
        if mode('CRAWL') is not True:raise RuntimeError('CRAWL mode was not accepted')
        target=(limits['max_vx'] if name=='forward' else -limits['max_vx'] if name=='reverse' else 0.,
            limits['max_wz'] if name=='left' else -limits['max_wz'] if name=='right' else 0.)
        try:
            source.set_target(*target)
            # A service ACK accepts authority, not physical controller motion.
            # Fail promptly if a latched explicit stop prevents the next phase.
            wait(lambda:snapshot()['motion_state']=='CRAWL',2.,name+' motion state')
            wait(lambda:_reached(start['pose'],snapshot()['pose'],name),900. if name=='forward' else 600.,name+' measured movement')
        finally:
            try:source.set_target(0.,0.)
            except RuntimeError:pass # already fault-closed; never reactivate it
        wait(lambda:source.smoothed==(0.,0.),2.,name+' smoothed zero')
        # Retain authorized CRAWL with a measured zero-velocity pause. Explicit
        # STAND latches the leg owner's stop and must not be auto-cleared merely
        # because a later CRAWL mode request was accepted (native f4157cd3).
        lease=MeasuredSettle(limits)
        wait(lambda:lease.update(snapshot()),10.,name+' measured settle')
        end=snapshot();phases[name]=dict(start=start['pose'],end=end['pose'],
            start_capture_ns=start['capture_ns'],end_capture_ns=end['capture_ns'],
            start_wall_ns=start['wall_ns'],end_wall_ns=end['wall_ns'])
    if mode('STAND') is not True:raise RuntimeError('final STAND mode was not accepted')
    set_stage('stopped');lease=MeasuredSettle(limits)
    def final_stopped():
        row=snapshot()
        return row['stage']=='stopped' and lease.update(row)
    wait(final_stopped,10.,'final measured settle')
    end=snapshot();phases['stopped']=dict(end=end['pose'],capture_ns=end['capture_ns'],wall_ns=end['wall_ns'])
    return phases
