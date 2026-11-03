"""Owned observation loss or duplicate action endpoint during actual arm motion."""
import argparse
import json
import os
import re
import signal
import sys
from pathlib import Path
import numpy as np
from rclpy.action import ActionClient,ActionServer,GoalResponse
from control_msgs.action import FollowJointTrajectory
from ch13_manipulation_reuse.action_bridge import ARM
from ch13_manipulation_reuse.trajectory import JOINTS


def owned_observer(out):
    matches=[]
    for raw in re.findall(r'process started with pid \[(\d+)\]',(out/'launch.log').read_text()):
        pid=int(raw);path=Path('/proc')/raw/'cmdline'
        if not path.exists():continue
        argv=path.read_bytes().decode().split('\0')
        if 'ch13_navigation_reuse.vision_approach' in argv and str(out/'engine.json') in argv:matches.append((pid,argv))
    assert len(matches)==1,'unique owned observer required'
    return matches[0]


def work(*,node,until,snapshot,status,control,out,case):
    from run_arm_probe import arm_goal
    arm=ActionClient(node,FollowJointTrajectory,ARM);extra=None;paused=None;record={'case':case};executed=[]
    try:
        assert until(arm.server_is_ready,3.)
        joints=snapshot()['joints'];q=dict(zip(joints.name,joints.position))
        request=arm_goal(np.array([q[j] for j in JOINTS]))
        sent=arm.send_goal_async(request);assert until(sent.done,3.);handle=sent.result();assert handle.accepted
        result=handle.get_result_async();start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=800_000_000,4.)
        if case=='observation_loss':
            paused=owned_observer(out);os.kill(paused[0],signal.SIGSTOP);record['paused_owned_observer_pid']=paused[0]
            expected='OBSERVATION_EXPIRED'
        else:
            def forbidden_execution(goal):
                executed.append(True);goal.abort();return FollowJointTrajectory.Result(error_code=-1)
            extra=ActionServer(node,FollowJointTrajectory,ARM,forbidden_execution,goal_callback=lambda request:GoalResponse.REJECT)
            expected='DUPLICATE_ACTION_SERVER'
        assert until(result.done,20.),'actual abort/hold terminal absent'
        terminal=result.result();assert terminal.status==6,(terminal,status())
        assert status()['phase']=='FAULT' and status()['fault']==expected,status()
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.),'actual settling absent'
        if paused is not None:
            pid,argv=paused;path=Path('/proc')/str(pid)/'cmdline'
            assert path.exists() and path.read_bytes().decode().split('\0')==argv
            os.kill(pid,signal.SIGCONT);paused=None
        if extra is not None:extra.destroy();extra=None
        before=snapshot()['clock_ns'];assert until(lambda:snapshot()['clock_ns']-before>=500_000_000,4.)
        assert status()['phase']=='FAULT' and status()['fault']==expected,'input recovery reactivated lease'
        assert not executed,'duplicate endpoint executed a goal'
        record.update(result='PASS',terminal=terminal.status,reason=terminal.result.error_string,expected_fault=expected,
                      no_auto_resume=True,duplicate_executions=len(executed))
    finally:
        if paused is not None:
            pid,argv=paused;path=Path('/proc')/str(pid)/'cmdline'
            if path.exists() and path.read_bytes().decode().split('\0')==argv:os.kill(pid,signal.SIGCONT)
        if extra is not None:extra.destroy()
        arm.destroy();(out/'safety_probe.json').write_text(json.dumps(record,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--evidence',required=True)
    parser.add_argument('--case',choices=['observation_loss','duplicate_action'],required=True);args=parser.parse_args();out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):raise ValueError('new evidence required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    from run_handoff import handoff
    return navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],
        handoff=lambda **context:handoff(**context,case=args.case,work=lambda **kw:work(**kw,out=out,case=args.case)))


if __name__=='__main__':sys.exit(main())
