"""10 Hz ROS BT node and one existing same-engine ROS owner worker."""
import argparse
import json
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
import py_trees
import py_trees_ros
from ch13_mission_orchestration.tasks import TaskPort,stop_worker
from ch13_mission_orchestration.tree import Mission
from ch13_mission_orchestration.session import Session
from ch13_mission_orchestration.tools import lift_interrupt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--evidence',required=True)
    ap.add_argument('--case',choices=['normal','cancel','low_battery','held_cancel'],default='normal')
    args=ap.parse_args();root=Path(args.repo_root);out=Path(args.evidence)
    if out.exists():raise ValueError('new evidence required')
    out.mkdir(parents=True)
    port=TaskPort();mission=Mission(port);session=Session(port);worker_result={}
    sys.path[:0]=[str(root/'Ch13/scripts/reuse_13_5'),str(root/'Ch13/scripts/reuse_13_6')]
    def worker():
        try:
            from run_navigation_probe import main as navigate
            from run_handoff import handoff
            from run_pick import work
            def manipulate(**context):
                def pick(**kw):session.pick_work(lambda **items:work(**items,out=out),evidence=out,**kw)
                return handoff(**context,case='bt',work=pick)
            code=navigate(['--repo-root',str(root),'--evidence',str(out),'--case','vision','--vision-hz','15'],
                planning=True,pick_scene=True,handoff=manipulate,orchestration=session)
            worker_result['exit_code']=code
            if code:port.fail('owned robot session failed; see navigation_summary.json')
            elif not session.cancel_requested():port.complete('finish',dict(session=session.session))
        except BaseException:
            code=1;worker_result['exception']=traceback.format_exc();port.fail(worker_result['exception'])
        finally:port.close(code)
    thread=threading.Thread(target=worker,name='bt_owned_robot_session',daemon=False)
    context=Context();rclpy.init(context=context);node=Node('ch13_bt_mission',context=context,
        parameter_overrides=[Parameter('default_snapshot_stream',value=True)])
    executor=SingleThreadedExecutor(context=context);executor.add_node(node)
    tree=py_trees_ros.trees.BehaviourTree(mission.root,unicode_tree_debug=False)
    tree.setup(node=node,timeout=5.)
    # tick() is driven here so terminal latching cannot silently restart the root.
    held_execution_start=None
    def tick():
        nonlocal held_execution_start
        progress=port.snapshot()['progress']
        if args.case in ('cancel','low_battery') and not session.cancel_requested() and progress.get('displacement_m',0)>.03 and progress.get('navigation_phase')=='ACTIVE':
            port.event('injection',case=args.case,progress=progress)
            if args.case=='low_battery':mission.battery=10.
            else:mission.stop_reason='user_cancel'
        if args.case=='held_cancel' and not session.cancel_requested():
            held_execution_start,inject=lift_interrupt(progress,held_execution_start)
            if inject:port.event('injection',case=args.case,progress=progress);mission.stop_reason='user_cancel'
        mission.tick(tree)
    timer=node.create_timer(.1,tick)
    def interrupt(*_):mission.stop_reason='user_cancel'
    previous=signal.signal(signal.SIGINT,interrupt)
    started=time.monotonic();thread.start()
    try:
        while thread.is_alive() or mission.terminal is None:
            executor.spin_once(timeout_sec=.05)
            if time.monotonic()-started>1200:
                port.fail('mission wall budget');port.cancel('mission_wall_budget')
        thread.join()
    except BaseException:
        worker_result['mission_exception']=traceback.format_exc();port.fail(worker_result['mission_exception'])
    finally:
        if not stop_worker(thread,port):port.fail('worker join deadline after mission exception')
        signal.signal(signal.SIGINT,previous);node.destroy_timer(timer)
        tree.shutdown(destroy_node=False);executor.remove_node(node);node.destroy_node();executor.shutdown();context.try_shutdown()
        data=port.snapshot()
        (out/'bt_ticks.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in mission.ticks))
        (out/'bt_summary.json').write_text(json.dumps(dict(profile='actual',case=args.case,terminal=mission.terminal,
            session=session.session,worker_joined=not thread.is_alive(),wall_s=time.monotonic()-started,
            port=data,worker=worker_result,goals=session.goals.audit()),indent=2)+'\n')
        (out/'tree.txt').write_text(py_trees.display.unicode_tree(mission.root,show_status=True))
        dot=py_trees.display.dot_tree(mission.root);dot.write_raw(str(out/'tree.dot'))
    return 0 if worker_result.get('exit_code')==0 and mission.terminal in ('SUCCESS','ABORTED') else 1


if __name__=='__main__':sys.exit(main())
