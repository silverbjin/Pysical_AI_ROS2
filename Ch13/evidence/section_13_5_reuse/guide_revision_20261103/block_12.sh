source "$HOME/physicalai_13_5/lab_env.sh"
RUN_OUT="$(cat "$REUSE_WORK/current_run.txt")"
tail -n 15 "$RUN_OUT/launch.log"
ros2 topic type /ch13/reuse/nav_cmd
ros2 topic type /ch13/reuse/cmd_vel_safe
ros2 topic info /ch13/reuse/cmd_vel_raw --verbose
timeout 5s ros2 topic echo /ch13/reuse/gateway/status --once
