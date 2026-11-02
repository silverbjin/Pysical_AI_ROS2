#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
task=.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO
bash "$task/build-native-s-observer.sh" task8-native-cdr-frozen
bash "$task/build-native-n.sh" task8-native-cdr-frozen
bash "$task/check-native.sh" task8-native-cdr-related-final \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_native_observer_cdr.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_native_probe.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_split_observer.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_observer_finalization.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_observer_capture_journal.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_runner_finalization.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_receiver_execution.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_journal_io.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_bounded_history.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_ingress_isolation.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_movement_decision.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_native_transport_ros.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_raw_tf.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_split_executor.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_serial_events_ros.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_probe_continuous_dispatch.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_applied_reference_event_deadline.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_applied_reference_credit.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_applied_reference_ros.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_reference_deferred_ack_ros.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_g2_control_cadence_ros.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_gait_reference_credit.py \
  Ch13/ros2_ws/src/integrated_robot_navigation/test/test_control_clock_runner.py
