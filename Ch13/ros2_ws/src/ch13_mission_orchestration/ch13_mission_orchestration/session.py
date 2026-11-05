"""Opt-in gates for the existing same-engine runner; one ROS owner thread."""
import copy
import json
import math
import time
from .tasks import GoalTracker,DeferredClients


def admit_observation(sample,clock_ns,wall):
    try:
        valid=(0<=wall-sample['capture_wall']<=.3 and
            -25_000_000<=clock_ns-sample['capture_ns']<=300_000_000 and
            0<=sample['capture_ns']-sample['tf_stamp_ns']<=100_000_000 and
            sample['capture_wall']<=sample['first_receipt_wall']<=wall+.01 and
            bool(sample['source_gids']) and len(sample['rgb_sha256'])==64 and
            len(sample['point'])==3 and all(math.isfinite(v) for v in sample['point']) and
            sample['source']=='actual_Renderer_RGBD_known_upright_cylinder_fit' and 'cylinder_fit' in sample)
    except (KeyError,TypeError,ValueError):valid=False
    if not valid:raise ValueError('live original cylinder observation required')
    return copy.deepcopy(sample)


class Session:
    def __init__(self,port):
        self.port=port;self.goals=GoalTracker();self.session=None;self.observed_session=None
        self.snapshot=None;self.origin=None;self.stopped=False;self.goal_id=None

    def ready(self,*,node,until,snapshot):
        from std_msgs.msg import String
        self.snapshot=snapshot
        def status(message):
            data=json.loads(message.data);self.observed_session=data.get('session')
            if self.session is None:self.session=self.observed_session
            self.port.progress(session=self.observed_session,manipulation_phase=data.get('phase'),task_phase=data.get('task_phase'))
        self.subscription=node.create_subscription(String,'/ch13/reuse/manipulation/status',status,16)
        assert until(lambda:self.session is not None,3.),'mission has no live session'
        self.await_step('navigate',until)

    def validate_session(self):
        if not self.session or self.session!=self.observed_session:raise ValueError('mission session changed')

    def await_step(self,name,until):
        assert until(lambda:name in self.port.snapshot()['requested'] or self.cancel_requested(),30.),'BT task start deadline: '+name
        if self.cancel_requested():raise RuntimeError('mission canceled before '+name)
        self.validate_session() if self.session else None
        self.port.event('started',task=name,session=self.session)

    def cancel_requested(self):return bool(self.port.snapshot()['cancel_reason'])

    def track_goal(self,sent):self.goals.add(sent)

    def poll(self):
        if self.cancel_requested():self.goals.cancel()
        self.goals.poll()
        if self.snapshot:
            current=self.snapshot();state=current['state']
            if state is not None:
                xy=(state.pose.pose.position.x,state.pose.pose.position.y)
                if self.origin is None:self.origin=xy
                self.port.progress(clock_ns=current['clock_ns'],
                    displacement_m=math.hypot(xy[0]-self.origin[0],xy[1]-self.origin[1]),
                    navigation_phase=current['boundary'].get('phase'),
                    stationary_ready=current['platform'].get('stationary_ready',False))

    def navigation_complete(self,payload):
        self.validate_session();self.goal_id=payload.get('goal_id');payload=dict(payload,session=self.session)
        self.port.event('navigation_terminal_and_settled',**payload)
        if not self.cancel_requested():self.port.complete('navigate',payload)

    def found(self,sample,clock_ns):
        self.validate_session();data=admit_observation(sample,clock_ns,time.monotonic())
        self.port.complete('find',dict(observation=data,session=self.session,goal_id=self.goal_id))

    def pick_work(self,callback,evidence=None,**context):
        """Keep force-hold on interruption; await terminal before lease revocation."""
        self.validate_session()
        # Every action future remains owned even if its calling behaviour exits.
        from rclpy.action import ActionClient
        tracker=self.goals;clients=DeferredClients(tracker)
        class OwnedClient(ActionClient):
            def __init__(inner,*args,**kwargs):
                super().__init__(*args,**kwargs)
                clients.defer(lambda:super(OwnedClient,inner).destroy())
            def send_goal_async(inner,*args,**kwargs):
                if self.cancel_requested():raise RuntimeError('BT canceled before next action send')
                sent=super().send_goal_async(*args,**kwargs);tracker.add(sent);return sent
            def destroy(inner):pass  # actual destruction follows result/cancel drain
        try:
            callback(action_client_factory=OwnedClient,**context)
            if not self.cancel_requested():self.port.complete('pick',dict(session=self.session))
        except BaseException:
            if not self.cancel_requested():raise
            until=context['until'];status=context['status'];snapshot=context['snapshot']
            assert until(lambda:tracker.drained,5.),'pending action terminal after BT cancel'
            assert not tracker.errors,tracker.errors
            saved=None
            if evidence is not None:
                from pathlib import Path
                path=Path(evidence)/'pick_mission.json'
                saved=json.loads(path.read_text()) if path.exists() else dict(stages=[],planning=[])
                saved['stages'].append(dict(held_cancel=5 in tracker.terminals,
                    actual_terminal='canceled' if 5 in tracker.terminals else 'between_actions_stop',source='BT_preemption'))
            context['control']['set_phase']('HOLD')
            start=snapshot()['clock_ns']
            if saved is not None:saved['stages'].append(dict(phase='HOLD',clock_ns=start))
            assert until(lambda:snapshot()['clock_ns']-start>=2.2e9 or status()['phase']=='FAULT',15.)
            assert status()['phase']!='FAULT',status()
            context['control']['set_phase']('POST_SETTLE')
            if saved is not None:saved['stages'].append(dict(phase='POST_SETTLE',clock_ns=snapshot()['clock_ns']))
            assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
            if saved is not None:path.write_text(json.dumps(saved,indent=2)+'\n')
            self.port.event('pick_canceled_and_settled',session=self.session)
        finally:clients.close(context['until'])
