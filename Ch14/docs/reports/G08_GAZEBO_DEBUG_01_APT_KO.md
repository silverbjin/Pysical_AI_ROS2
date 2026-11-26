# G08-D 환경 디버깅 01 — APT index mismatch

OBSERVE: Run [45798971449](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45798971449) exit100, artifact15106606988 ZIP SHA256 9e6e16888aa3287ee628155068e5150e343defe08380068f44495b440c1f8aa6, 4/4 internal verified. G07 model reuse 11 passed. Ubuntu security HTTP Packages.gz size 1513663 vs expected1513652; updates HTTP Packages.gz SHA256 153121a6... vs expected63682d0b.... 
ISOLATE: stage locked_environment, before colcon and Gazebo; no simulation, no policy failure. Mirror sync/cache inconsistency is hypothesis, not proven server root cause.
FIX: only G08 Gazebo isolated container changes Ubuntu official endpoints to HTTPS, cache bypass request and bounded APT retries, fatal index error retained. No signatures/hash checks disabled, no lock/package/controller changes. One targeted fresh run; same fingerprint bounded per policy. Existing MuJoCo evidence preserved. VERIFY pending.

VERIFY: targeted retry 45799511462 SUCCESS, artifact15106482820 25/25 verified, actual Gazebo 399/399/50Hz, all exits0. No additional environment change needed.
