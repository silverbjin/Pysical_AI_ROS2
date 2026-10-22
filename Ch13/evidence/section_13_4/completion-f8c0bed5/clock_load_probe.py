"""Non-engine attribution probe: identical 500Hz clock, idle mission node.

No runtime configuration changes; uses an isolated ROS domain from the caller.
CPU time is process CPU / wall, not a scheduling-deadline guarantee.
"""
import json
import multiprocessing as mp
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rosgraph_msgs.msg import Clock
from integrated_robot_runtime.mission import MissionCommander


def clock_source(stop):
    rclpy.init()
    node = rclpy.create_node('clock_probe_source')
    publisher = node.create_publisher(Clock, '/clock', 10)
    start = time.monotonic()
    def send():
        ns = int((100 + time.monotonic() - start) * 1e9)
        msg = Clock()
        msg.clock.sec, msg.clock.nanosec = divmod(ns, 1_000_000_000)
        publisher.publish(msg)
    node.create_timer(.002, send)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        while not stop.is_set():
            executor.spin_once(timeout_sec=.01)
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    context = mp.get_context('spawn')
    stop = context.Event()
    publisher = context.Process(target=clock_source, args=(stop,))
    publisher.start()
    results = []
    try:
        for threads in (0, 1, 4):
            rclpy.init(args=['--ros-args', '-p', 'use_sim_time:=true'])
            node = MissionCommander()
            executor = (MultiThreadedExecutor(num_threads=threads) if threads
                        else SingleThreadedExecutor())
            executor.add_node(node)
            try:
                warmup = time.monotonic() + 2
                while time.monotonic() < warmup:
                    executor.spin_once(timeout_sec=.01)
                start_wall, start_cpu = time.monotonic(), time.process_time()
                initial = node.get_clock().now().nanoseconds
                spins = 0
                while time.monotonic() - start_wall < 5:
                    executor.spin_once(timeout_sec=.01)
                    spins += 1
                results.append(dict(executor_threads=threads, spins=spins,
                    cpu_seconds=time.process_time()-start_cpu,
                    wall_seconds=time.monotonic()-start_wall,
                    clock_advance_ns=node.get_clock().now().nanoseconds-initial))
            finally:
                executor.shutdown()
                node.destroy_node()
                rclpy.shutdown()
    finally:
        stop.set()
        publisher.join(timeout=10)
        if publisher.is_alive():
            raise RuntimeError('owned clock probe did not stop')
    print(json.dumps(results, indent=2))
