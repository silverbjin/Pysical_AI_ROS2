# Ch15 ICD — G02 구현 상태
| IF | endpoint | type / QoS | 구현 상태 |
|---|---|---|---|
|01|/scan|LaserScan BE/V/1 10Hz|MOCK|
|02|/camera/image_raw|Image BE/V/1|G04|
|03|/ch15/target_pose|PoseStamped R/V/1|G03/04|
|04|/navigate_to_pose|NavigateToPose default action|MOCK|
|05|/pick_object|PickObject default action|MOCK|
|06|/cmd_vel|Twist R/V/1 20Hz|sole mock arbiter|
|07|/place_object|PlaceObject default action|MOCK|
|08|/switch_gait|SwitchGait service|MOCK|
|09|/ch15/mission_state|MissionStatus R/TL/10|G03|
|10|/ch15/stop_request|Bool R/V/10 20Hz|watchdog|
|11|/ch15/cmd_vel_in|TwistStamped R/V/1 20Hz|mock nav|
|12|/ch15/target_observation|TargetObservation R/V/1|G03/04|
|13|/ch15/safety_state|SafetyState R/TL/10|arbiter|
|14|/ch15/mission_event|MissionEvent R/V/100|G03|
|15|/ch15/ready|ReadyState R/V/1 10Hz|monitor|
|16|/ch15/gait_state|String R/TL/1 10Hz|mock|
|17|/ch15/mission_state_demo|String R/TL/10|qos demo|
|18|/ch15/start_mission, /ch15/cancel_mission, /ch15/reset_safety|Trigger|start/cancel G03; reset rejects G02|
|19|/tf, /tf_static etc|native types|mock static TF only; do not synthesize others|
Extra G02 teaching witnesses /ch15/mock_witness String R/V/10 and /ch15/qos_demo/sensor String BE/V/10 (controlled 10 samples). Native Ch13 contract separate. Exact IDL files authoritative. No actuator or real robot.
