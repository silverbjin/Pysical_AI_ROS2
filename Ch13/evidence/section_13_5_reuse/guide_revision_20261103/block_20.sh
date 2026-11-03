source "$HOME/physicalai_13_5/lab_env.sh"
ros2 action list -t
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
timeout 5s ros2 topic echo /ch13/reuse/observed_target --once
timeout 5s ros2 topic echo /ch13/reuse/navigation/status --once
ros2 param get /controller_server goal_checker.xy_goal_tolerance
ros2 param get /controller_server FollowPath.desired_linear_vel
