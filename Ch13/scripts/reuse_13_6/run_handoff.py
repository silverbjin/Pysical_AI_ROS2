"""Same-engine live handoff acceptance; delegates navigation to its sole owner."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from std_msgs.msg import String
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from ch13_navigation_reuse.command_gateway import N


def handoff(*, node, until, call, out, goal_id, target, snapshot, case='hold', work=None):
    validation = os.environ.get('CH13_VALIDATION_PROFILE') == 'carry_v1'
    owner_gc = None
    if validation:
        from ch13_manipulation_reuse.gc_timing import GCTiming
        owner_gc = GCTiming()
    status = {}
    rows = []
    beats = []
    sequence = 0
    revoked = False
    enabled = True
    task_phase = 'WAITING'
    transport = {}
    def on_status(message):
        nonlocal status
        status = json.loads(message.data)
        # Control reads the parsed current sample; history needs no object graph.
        # Preserve ordinary JSON verbatim, normalize multiline JSON to one row.
        if validation:
            raw = message.data
            rows.append(json.dumps(status) if '\n' in raw or '\r' in raw else raw)
        else:
            rows.append(dict(status))
    subscription = node.create_subscription(String,N+'/manipulation/status',on_status,16)
    publisher = node.create_publisher(String,N+'/manipulation/lease',1)
    timer = None
    extra = None
    try:
        if owner_gc is not None:
            owner_gc.start()
        assert until(lambda:bool(status.get('session')),3.),'no live engine session'
        session = status['session']
        def beat():
            nonlocal sequence
            if not enabled:
                return
            current = snapshot()
            sample = current['observation']
            if sample is None:
                return
            sequence += 1
            message = dict(session='past-session' if case=='old_session' else session,
                           goal_id=goal_id,terminal=4,target=target,sequence=sequence,
                           stamp_ns=current['clock_ns'],capture_ns=sample['capture_ns'],
                           state='REVOKE' if revoked else 'OFFER',task_phase=task_phase)
            message.update(transport)
            sent=time.monotonic();publisher.publish(String(data=json.dumps(message)))
            beats.append(dict(sequence=sequence,stamp_ns=message['stamp_ns'],capture_ns=message['capture_ns'],
                              send_wall=sent,publish_return_wall=time.monotonic()))
        timer = node.create_timer(.05,beat,clock=Clock(clock_type=ClockType.STEADY_TIME))
        if case=='old_session':
            assert until(lambda:status.get('phase')=='FAULT',2.),'old session admitted'
            assert status['fault']=='SESSION_MISMATCH',status
        else:
            assert until(lambda:status.get('phase') in ('READY','FAULT'),3.),'lease admission deadline'
            assert status['phase']=='READY',status
            start = time.monotonic()
            if case=='hold':
                assert until(lambda:time.monotonic()-start>=2. or status.get('phase')=='FAULT',3.)
                assert status['phase']=='READY',status
            elif case=='expire':
                enabled = False
                assert until(lambda:status.get('phase')=='FAULT',2.),'lost heartbeat still admitted'
                assert status['fault']=='MISSION_EXPIRED',status
            elif case=='duplicate':
                extra = node.create_publisher(String,N+'/manipulation/lease',1)
                assert until(lambda:status.get('phase')=='FAULT',2.),'duplicate publisher admitted'
                assert 'DUPLICATE_OWNER:mission'==status['fault'],status
            elif work is not None:
                def disable():
                    nonlocal enabled
                    enabled=False
                def set_phase(value):
                    nonlocal task_phase
                    task_phase=value
                    assert until(lambda:status.get('task_phase')==value or status.get('phase')=='FAULT',2.)
                    assert status.get('phase')!='FAULT',status
                def reserve(goal,target):
                    transport.update(transport_goal_id=goal,transport_target=list(target))
                work(node=node,until=until,snapshot=snapshot,status=lambda:status,control={'disable_heartbeat':disable,'set_phase':set_phase,'reserve_transport':reserve})
            if status.get('phase')!='FAULT':
                revoked = True
                assert until(lambda:status.get('phase')=='REVOKED',2.),'explicit handoff revoke failed'
        return dict(result='PASS',case=case,session=session,goal_id=goal_id,
                    final_status=status,live_status_samples=len(rows))
    finally:
        if owner_gc is not None:
            owner_gc.stop()
        if timer is not None:
            node.destroy_timer(timer)
        node.destroy_subscription(subscription)
        if extra is not None:
            node.destroy_publisher(extra)
        node.destroy_publisher(publisher)
        (out/'manipulation_status.jsonl').write_text(''.join(
            (r if validation else json.dumps(r))+'\n' for r in rows))
        (out/'mission_heartbeats.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in beats))
        if owner_gc is not None:
            (out/'owner_gc_timing.json').write_text(json.dumps(owner_gc.summary(),indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-root',required=True)
    parser.add_argument('--evidence',required=True)
    parser.add_argument('--case',choices=['hold','expire','old_session','duplicate'],default='hold')
    args=parser.parse_args()
    out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):
        raise ValueError('new evidence directory required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    return navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],
                    handoff=lambda **context:handoff(**context,case=args.case))


if __name__=='__main__':
    sys.exit(main())
