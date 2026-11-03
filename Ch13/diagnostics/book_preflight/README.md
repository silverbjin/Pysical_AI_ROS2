# Frozen operational preflight source

This is the exact source used by the existing native lease owner in this work.
It adds the changed explicit-stop ROS boundary tests to the existing stable-clock
CPU/RPC verification, before any native engine is started. Clock/service scope,
first-failure stop and cleanup policy are unchanged. The installed book example
does not require this workstation-specific operational wrapper. Runtime tests
and launch examples remain under `Ch13/ros2_ws` and `Ch13/scripts`.

The unleased attempt failed during activation with
`command_clock_step_requires_restart` before exercising fault-stop behavior;
its original failure log is retained. New ROS acceptance is pending this
pre-engine verification and must not be counted as passing beforehand.
