#!/usr/bin/env python3
"""Run a bounded native contact component WITHOUT changing G2 acceptance.

The original G2 runner/checks/result stay intact. Missing full movement/yaw
phases keep its result FAIL. The separate component report is never admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
import run_navigation_13_5 as runner
from integrated_robot_navigation.contact_component import (
    ContactTransitionTracker,ComponentCaptureJoiner,observe_contact_cycle,component_outcome)
from integrated_robot_navigation.observations import sensor_sample
from integrated_robot_navigation.g2_sequence import MeasuredSettle
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import load_scene


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('scene-dir','profile','g1-result','output-dir'):parser.add_argument('--'+key,required=True)
    args=parser.parse_args();output=Path(args.output_dir)
    model=compile_model(Path(load_scene('gazebo',args.scene_dir)['robot']['path']).read_text())
    context=dict(probe=None,tracker=None,joiner=None,finished=False,error=None,
        cycles=dict(count=0,first_wall_ns=None,last_wall_ns=None,minimum_interval_ns=None,
            maximum_consumed_captures=0,total_consumed_captures=0))
    original_factory=runner.make_native_probe

    def factory(directory,*,engine,**kwargs):
        probe=original_factory(directory,engine=engine,**kwargs)
        joiner=ComponentCaptureJoiner();original_sensor=probe._sensor
        def component_sensor(key,msg,info=None,*,receipt_ns=None,system_ns=None):
            # Reuse ONE callback-entry receipt for the unchanged mission probe
            # and this read-only capture history. Never retag at association.
            receipt=time.monotonic_ns() if receipt_ns is None else receipt_ns
            original_sensor(key,msg,info,receipt_ns=receipt,system_ns=system_ns)
            if key in joiner.keys:
                sample=sensor_sample(key,msg,receipt,0)
                with probe._lock:joiner.receive(key,sample)
        probe._sensor=component_sensor
        # Only this component diagnostic adds joint READ ingress to the light
        # mission probe. No new command/TF/joint publisher or executor is added.
        probe.ingress_node.create_subscription(JointState,'/joint_states',
            lambda msg,info:probe._dispatch(probe._sensor,'joints',msg,info),qos_profile_sensor_data)
        context['probe']=probe;context['joiner']=joiner
        return probe

    def frame(*,begin=False):
        probe=context['probe']
        with probe._lock:
            ros=probe.get_clock().now().nanoseconds;wall=time.monotonic_ns()
            joiner=context['joiner']
            return joiner.begin(ros,wall) if begin else joiner.take(ros,wall)

    def sequence(scenario,*,snapshot,source,mode,wait,set_stage,limits):
        if scenario!='crawl-cycle':raise ValueError('component requires the unchanged forward G2 profile')
        due=[0]
        def observed():
            now=time.monotonic_ns()
            if now<due[0]:return False
            due[0]=now+20_000_000
            metrics=context['cycles'];previous=metrics['last_wall_ns']
            if previous is None:metrics['first_wall_ns']=now
            else:
                gap=now-previous;old=metrics['minimum_interval_ns']
                metrics['minimum_interval_ns']=gap if old is None else min(old,gap)
            metrics['last_wall_ns']=now;metrics['count']+=1;before=tracker.samples
            try:return observe_contact_cycle(tracker,frame)
            finally:
                used=tracker.samples-before
                metrics['maximum_consumed_captures']=max(metrics['maximum_consumed_captures'],used)
                metrics['total_consumed_captures']+=used
        try:
            set_stage('forward');start=snapshot()
            if mode('CRAWL') is not True:raise RuntimeError('component CRAWL rejected')
            # Mode RPC may wait; start the finite capture queue only after
            # its ACK, while the source still requests zero and all four
            # measured supports are required for the baseline.
            baseline=frame(begin=True)
            if baseline is None:raise ValueError('contact component coherent baseline unavailable')
            tracker=ContactTransitionTracker(model,baseline);context['tracker']=tracker
            source.set_target(limits['max_vx'],0.)
            def moving():
                observed()  # drain in capture order during mode publication latency too
                return snapshot()['motion_state']=='CRAWL'
            wait(moving,2.,'component motion state')
            wait(observed,180.,'four physical unload/lift/return transitions')
        finally:
            with context['probe']._lock:context['joiner'].close()
            try:source.set_target(0.,0.)
            except RuntimeError:pass  # never reopen a latched command source
        wait(lambda:source.smoothed==(0.,0.),2.,'component smoothed zero')
        settle=MeasuredSettle(limits)
        wait(lambda:settle.update(snapshot()),10.,'component measured pause settle')
        end=snapshot()
        if mode('STAND') is not True:raise RuntimeError('component explicit STAND rejected')
        set_stage('stopped');settle=MeasuredSettle(limits)
        wait(lambda:settle.update(snapshot()),10.,'component explicit measured stop')
        stopped=snapshot();context['finished']=True
        return dict(forward=dict(start=start['pose'],end=end['pose'],
            start_capture_ns=start['capture_ns'],end_capture_ns=end['capture_ns'],
            start_wall_ns=start['wall_ns'],end_wall_ns=end['wall_ns']),
            stopped=dict(end=stopped['pose'],capture_ns=stopped['capture_ns'],wall_ns=stopped['wall_ns']))

    runner.make_native_probe=factory;runner.run_sequence=sequence
    native=argparse.Namespace(engine='gazebo',scenario='crawl-cycle',scene_dir=args.scene_dir,
        profile=args.profile,g1_result=args.g1_result,output_dir=args.output_dir,
        control_clock_mode='relay100',dart_contact_mode='allowance50um',observer_backend='native_cdr',profile_node=None)
    try:runner.run_with_retention(native)
    except BaseException as error:context['error']=repr(error)
    finally:
        if context['joiner'] is not None:
            with context['probe']._lock:context['joiner'].close()
    result=json.loads((output/'result.json').read_text())
    records=(json.loads((output/'native_controls.json').read_text())['records']
        if (output/'native_controls.json').exists() else [])
    provider=(json.loads((output/'dart_contact_probe.json').read_text())
        if (output/'dart_contact_probe.json').exists() else None)
    dart=runner.assess_dart_contact_configuration(records,provider,scenario='contact-component')
    tracker=context['tracker'].report() if context['tracker'] else dict(all_four_contacts_completed=False)
    association=context['joiner'].report() if context['joiner'] else None
    if association is not None:
        joiner=context['joiner'];pending=joiner.history['contacts']
        oldest=pending[min(pending)] if pending else None
        association.update(last_evaluation_ros_ns=joiner.last_ros,last_evaluation_wall_ns=joiner.last_wall,
            oldest_pending=None if oldest is None else dict(capture_ns=oldest.stamp_ns,received_ns=oldest.received_ns))
    outcome=component_outcome(result,tracker,protocol_finished=context['finished'],dart_observed=dart['passed'])
    outcome.update(error=context['error'],dart_component_assessment=dart,
        capture_association=association,
        observation_cycles=context['cycles'],
        original_result_sha256=hashlib.sha256((output/'result.json').read_bytes()).hexdigest(),
        method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        maximum_component_wall_s=180.,maximum_observation_rate_hz=50.,
        observation_rate_scope='wall read cycles; already received contact captures consumed FIFO within each cycle',
        maximum_captures_consumed_per_cycle=ComponentCaptureJoiner.capacity,
        creates_new_captures=False,
        added_read_topic='/joint_states',no_new_command_or_tf_publishers=True)
    if not association or association['closed'] is not True or association['error']:
        outcome['observations_complete']=False
    (output/'contact_component.json').write_text(json.dumps(outcome,indent=2))
    print(json.dumps(dict(path=str(output),observations_complete=outcome['observations_complete'],
        full_G2_acceptance=False,original_G2_status=result['status'])),flush=True)
    return 0 if outcome['observations_complete'] and context['error'] is None else 1


if __name__=='__main__':raise SystemExit(main())
