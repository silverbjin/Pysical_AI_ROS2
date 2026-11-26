# G03 D01 — rclpy Node.clients property collision
2026-11-27 KST. Original source 27e7efbb324669956709242a0d302933069436ee, run [45857297181](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45857297181), artifact [15136755861](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45857297181/artifacts/15136755861), SHA256 4c23315239422e863c42eb96943bff83b511cd42d70c031769c0e876a7530ec5. Downloaded original ZIP 22783 bytes; independent SHA256 matches and all 18 internal hashes checked. py_trees 2.6.0.
## RED/partial GREEN
Against pre-G03 source, import error missing ActionSupervisor (expected RED). Current 10+3+3 pure tests PASS; four packages build 12.5s. Actual DDS T06 eight cases PASS; accepted 7/7 terminal, rejected case has no accepted UUID; cancel delays 0.021063418 / 0.372531484 / 0.017914936 s. Late/unconfirmed each latch at 2s, late terminals at 2.555428 / 2.555841s; FAILED retained. Fixture exit0 force false.
## Failure evidence
Full mission process failed during __init__, before START; executor log:
```
self.clients={k:ActionClient(self,a,n) ...}
AttributeError: property 'clients' of 'MissionExecutor' object has no setter
```
Three children started, executor exit1, other two exit0, force false. Event file empty; tick header only. Thus T08/09 FAIL on original pin. No mission or movement success.
## Root cause and decision
Python subclass of rclpy.node.Node has read-only clients property. Custom registry name collided with framework API; not DDS/QoS/BT timing. Rename only to _action_clients (init and references). Do not change gate, timeouts or DDS contracts. Original T06 code/test closure unchanged. Dedicated mission-only CI, no repeated prior successes. Further verdict requires real new log.
