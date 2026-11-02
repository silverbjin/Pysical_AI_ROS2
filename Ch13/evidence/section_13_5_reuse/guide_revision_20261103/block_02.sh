mkdir -p "$HOME/physicalai_13_5"
cd "$HOME/physicalai_13_5"
git clone --filter=blob:none --sparse --depth 1 --single-branch \
  --branch feat/ch13-section-13-5-reuse-r2-20261102 \
  https://github.com/silverbjin/Pysical_AI_ROS2.git Pysical_AI_ROS2
cd Pysical_AI_ROS2
git sparse-checkout set Ch13/docs Ch13/dependencies Ch13/scripts/reuse_13_5 \
  Ch13/ros2_ws/src/ch13_navigation_reuse Ch13/ros2_ws/src/ch13_reuse_wire \
  Ch13/ros2_ws/src/integrated_robot_vision Ch13/evidence/section_13_5_reuse
git rev-parse HEAD
