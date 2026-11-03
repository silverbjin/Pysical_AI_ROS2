cat > "$HOME/physicalai_13_5/lab_env.sh" <<'BASH_ENV'
export REUSE_WORK="$HOME/physicalai_13_5"
export REUSE_REPO="$REUSE_WORK/Pysical_AI_ROS2"
export CH13_REUSE_VENV="$REUSE_WORK/venv_reuse"
export CH13_REUSE_BUILD="$REUSE_WORK/build_reuse"
export EVIDENCE_ROOT="$REUSE_REPO/Ch13/evidence/section_13_5_reuse"
export REUSE_PKG="$REUSE_REPO/Ch13/ros2_ws/src/ch13_navigation_reuse"
export ROS_DOMAIN_ID=135
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
source /opt/ros/jazzy/setup.bash
if [[ -f "$CH13_REUSE_BUILD/install/setup.bash" ]]; then
  source "$CH13_REUSE_BUILD/install/setup.bash"
fi
cd "$REUSE_REPO"
BASH_ENV
source "$HOME/physicalai_13_5/lab_env.sh"
