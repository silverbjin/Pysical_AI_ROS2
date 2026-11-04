"""Chapter 13.8 extends the existing BT owner; one live engine throughout."""
import argparse
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import time
import uuid
import hashlib
from pathlib import Path
from statistics import mean


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--evidence',required=True)
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--auto-start',action='store_true');ap.add_argument('--no-bag',action='store_true')
    args=ap.parse_args();root=Path(args.repo_root).resolve();out=Path(args.evidence).resolve()
    manifest=Path(args.manifest).resolve()
    subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(manifest)],check=True)
    os.environ['CH13_VALIDATION_PROFILE']='carry_v1'
    from std_msgs.msg import Empty,String
    from sensor_msgs.msg import LaserScan,JointState
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    import py_trees
    from ch13_mission_orchestration.tree import Mission,Task
    from ch13_mission_orchestration.tasks import TaskPort,STEPS
    from ch13_mission_orchestration.session import Session
    from ch13_system_validation.continuation import continue_mission
    from ch13_system_validation.monitor import TopicStats,ProcessCPU
    from ch13_navigation_reuse.command_gateway import N,ns
    from ch13_system_validation.physics import assess_transport
    from ch13_manipulation_reuse.pick_acceptance import assess_pick

    class ValidationSession(Session):
        engine_budget_sim_s=600.
        def ready(self,**context):
            from ch13_system_validation.startup import prepare_manipulation_types
            # All of this stays on the ROS owner before a manipulation OFFER.
            for record in prepare_manipulation_types():self.port.event('startup_preparation',**record)
            super().ready(**context)

    class WaitStart(py_trees.behaviour.Behaviour):
        def __init__(self,mission):super().__init__('Wait /start_mission');self.m=mission
        def update(self):return py_trees.common.Status.SUCCESS if self.m.started else py_trees.common.Status.RUNNING

    class ValidationMission(Mission):
        def __init__(self,port):
            super().__init__(port);self.started=False
            main=self.root.children[-1];finish=main.children[-1];main.remove_child(finish)
            main.insert_child(WaitStart(self),0)
            main.add_children([Task('return',self),Task('place',self),finish])
            self.log=None
        def tick(self,tree=None):
            super().tick(tree)
            if self.log is not None and self.ticks:
                latest=self.ticks[-1]
                self.log.publish(String(data=json.dumps({k:latest[k] for k in ('tick','root','nodes','terminal')})))

    health={};clock=[None];tilts=[];cpu=ProcessCPU();bag=[None];mission_ref=[None];start=[None]
    def configure(node,mission):
        (out/'source_manifest.json').write_bytes(manifest.read_bytes())
        stage=root.parent/'source_stage.json'
        if stage.exists():
            staged=json.loads(stage.read_text())
            assert staged['runtime_root']==str(root) and staged['source_manifest_sha256']==hashlib.sha256(manifest.read_bytes()).hexdigest(),'runtime staging provenance mismatch'
            (out/'runtime_stage.json').write_bytes(stage.read_bytes())
        mission.log=node.create_publisher(String,N+'/validation/bt_log',1)
        mission_ref[0]=mission
        def trigger(_):
            if not mission.started:
                mission.started=True;start[0]=(clock[0],time.monotonic())
                mission.port.event('start_mission_received')
        node.create_subscription(Empty,'/start_mission',trigger,1)
        node.create_subscription(Clock,'/clock',lambda msg:clock.__setitem__(0,ns(msg.clock)),1)
        def sample(name,msg):
            stats=health.setdefault(name,TopicStats())
            if isinstance(msg,String):
                value=json.loads(msg.data);stamp=value.get('capture_ns');capture=value.get('capture_wall')
            else:stamp=ns(msg.header.stamp);capture=None
            stats.add(stamp,time.monotonic(),clock_ns=clock[0],capture_wall=capture)
            if isinstance(msg,Odometry) and mission.started:
                q=msg.pose.pose.orientation
                roll=math.atan2(2*(q.w*q.x+q.y*q.z),1-2*(q.x*q.x+q.y*q.y))
                pitch=math.asin(max(-1.,min(1.,2*(q.w*q.y-q.z*q.x))))
                tilts.append(max(abs(roll),abs(pitch)))
        for name,kind in (('/scan',LaserScan),('/joint_states',JointState),('/engine_state',Odometry),('/vision/observation',String)):
            node.create_subscription(kind,N+name,lambda msg,n=name:sample(n,msg),1)
        node.create_timer(1.,cpu.sample)
        def live_status():
            data=mission.port.snapshot()
            temporary=out/'live_status.tmp'
            temporary.write_text(json.dumps(dict(terminal=mission.terminal,requested=data['requested'],
                completed=list(data['completed']),progress=data['progress'],error=data['error'],wall=time.monotonic()),indent=2)+'\n')
            temporary.replace(out/'live_status.json')
        node.create_timer(1.,live_status)
        if not args.no_bag:
            bag[0]=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','bag','record','--use-sim-time',
                '-o',str(out/'bag'),'/clock','/tf','/tf_static',N+'/joint_states',N+'/odometry',N+'/cmd_vel_safe',
                N+'/vision/observation',N+'/vision/health',N+'/manipulation/status',N+'/navigation/status',
                N+'/validation/bt_log','/start_mission'],
                stdout=(out/'bag.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
        if args.auto_start:
            publisher=node.create_publisher(Empty,'/start_mission',1)
            def automatic():
                if clock[0] is not None and clock[0]>2_000_000_000 and not mission.started:publisher.publish(Empty())
            node.create_timer(.25,automatic)

    spec=importlib.util.spec_from_file_location('bt13_7_runner',root/'Ch13/scripts/reuse_13_7/run_mission.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    code=1
    try:
        code=runner.main(['--repo-root',str(root),'--evidence',str(out)],mission_factory=ValidationMission,
                         session_factory=ValidationSession,port_factory=lambda:TaskPort(STEPS+('place',)),pick_continuation=continue_mission,configure=configure)
    finally:
        bag_closed=None
        if bag[0] is not None:
            if bag[0].poll() is None:bag[0].send_signal(signal.SIGINT)
            try:bag[0].wait(timeout=15);bag_closed=bag[0].returncode==0
            except subprocess.TimeoutExpired:
                bag_closed=False;bag[0].terminate();bag[0].wait(timeout=5.)
        if out.exists():
            summary=json.loads((out/'bt_summary.json').read_text()) if (out/'bt_summary.json').exists() else {}
            mission=mission_ref[0];completed={} if mission is None else mission.port.snapshot()['completed']
            place=completed.get('place',{});began=start[0]
            engine=json.loads((out/'engine.json').read_text()) if (out/'engine.json').exists() else {}
            physical_rows=engine.get('pick_physics',{}).get('rows',[])
            physics=dict(pick=assess_pick(physical_rows),transport=assess_transport(physical_rows))
            physical_ok=all(v['result']=='PASS' for v in physics.values())
            finished=place.get('wall',time.monotonic())
            mission_cpu=[r['percent'] for r in cpu.rows if began and began[1]<=r['wall']<=finished]
            sim_s=None if not began or began[0] is None else (place.get('clock_ns',clock[0] or began[0])-began[0])/1e9
            row=dict(uuid=out.name,complete=summary.get('worker_joined') is True and summary.get('port',{}).get('closed') is True,
                success=code==0 and summary.get('terminal')=='SUCCESS' and 'place' in completed and physical_ok and (args.no_bag or bag_closed is True),
                sim_s=sim_s,wall_s=None if not began else finished-began[1],
                position_error_m=completed.get('return',{}).get('position_error_m'),
                max_tilt_rad=max(tilts) if tilts else None,cpu_percent=mean(mission_cpu) if mission_cpu else None,
                bag_closed=bag_closed,profile='actual',level='continuous_development_fixture',
                cpu_basis='owned process tree / sched_getaffinity cores',allowed_cores=cpu.cores)
            row.update(source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),physical=physics)
            (out/'trial.json').write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
            (out/'health.json').write_text(json.dumps(dict(topics={k:v.report() for k,v in health.items()},cpu=cpu.rows,
                battery_voltage='unavailable: no physical voltage model'),indent=2)+'\n')
    return 0 if code==0 and row['success'] else 1


if __name__=='__main__':sys.exit(main())
