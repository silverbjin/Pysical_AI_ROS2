"""Same-engine live handoff acceptance; delegates navigation to its sole owner."""
import argparse
import json
import sys
import time
from pathlib import Path
from std_msgs.msg import String
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from ch13_navigation_reuse.command_gateway import N


def handoff(*, node, until, call, out, goal_id, target, snapshot, case='hold', work=None):
    status = {}
    rows = []
    sequence = 0
    revoked = False
    enabled = True
    def on_status(message):
        nonlocal status
        status = json.loads(message.data)
        rows.append(dict(status))
    subscription = node.create_subscription(String,N+'/manipulation/status',on_status,16)
    publisher = node.create_publisher(String,N+'/manipulation/lease',1)
    timer = None
    extra = None
    try:
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
                           state='REVOKE' if revoked else 'OFFER')
            publisher.publish(String(data=json.dumps(message)))
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
                work(node=node,until=until,snapshot=snapshot,status=lambda:status)
            if status.get('phase')!='FAULT':
                revoked = True
                assert until(lambda:status.get('phase')=='REVOKED',2.),'explicit handoff revoke failed'
        return dict(result='PASS',case=case,session=session,goal_id=goal_id,
                    final_status=status,live_status_samples=len(rows))
    finally:
        if timer is not None:
            node.destroy_timer(timer)
        node.destroy_subscription(subscription)
        if extra is not None:
            node.destroy_publisher(extra)
        node.destroy_publisher(publisher)
        (out/'manipulation_status.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))


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
