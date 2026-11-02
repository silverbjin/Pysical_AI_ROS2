# Reuse manifest — section_13_5_reuse_v1

Upstream: https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab/tree/d010212c3f5c9e6e5542ada61cfdacc19b00f775

Original source: deploy/play_mujoco.py, deploy/config.py, deploy/locomotion_policy_wrapper.py. Exact source/model/policy hashes are in Ch13/dependencies/section_13_5_reuse.lock.json. Root license notice is preserved in third_party/IIT_DLSLab_BSD-3-Clause.txt. Copyright (c) 2026, DLS Lab at Istituto Italiano di Tecnologia, Italy.

Ch13's helper is opt-in, simulator-specific and is not an upstream release:

1. Copy the initial arm target out of the mutable engine qpos view.
2. Represent the same arm PD50/4 with affine MuJoCo actuators and implicitfast. Original32/8Nm force caps remain enforced. Arm ctrl now means joint position target, so the replay overwrites arm ctrl before every step.
3. Preserve original walking20/1.5 on non-inference ticks while RL is active. Keep stand50/5 when RL is inactive. Only two conditional gain-selection assignments are changed in an in-memory copy of the original run method.

Evidence/section_13_5_reuse/0a384893-e928-4a23-919c-3d98b51f51be contains the exact corrected run source and two-line patch. These are derived upstream source and retain the above BSD notice by this manifest and the bundled license. The upstream checkout itself is not edited.

No policy weights, robot meshes or XML model assets are copied into this change. Third-party asset redistribution provenance remains separate from the source-code BSD notice. Original experiments and failed corrected profiles are preserved as failures.

R2 uses ch13_navigation_reuse and ch13_reuse_wire. These add standard ROS state/TF and guarded velocity I/O around the same pinned loop; the split upstream ROS scripts and their import-time priority writes are not run. The helper and BSD notice are installed byte-for-byte as package data. rclcpp ingress contains no upstream policy/physics code. Source/model/weight originals remain read-only.
