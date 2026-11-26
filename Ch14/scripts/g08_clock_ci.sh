#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=verify_reuse
trap 'rc=$?; printf "{\"stage\":\"%s\",\"exit_code\":%d}\n" "$stage" "$rc" > "$out/stage.json"' EXIT
python3 /ch14/scripts/g07_verify_reuse.py --root /reuse | tee "$out/reuse.json"
test -s /ch14/requirements/rl.lock.txt
stage=locked_environment
# Only the isolated G08 container: preserve apt signatures and hash checks.
# First run observed stale HTTP indexes (size and digest mismatch).
for f in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do
  if [[ -f "$f" ]]; then
    sed -i -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' "$f"
    cat "$f" >> "$out/ubuntu-apt-sources.txt"
  fi
done
printf '%s\n' 'Acquire::Retries "2";' 'Acquire::http::No-Cache "true";' 'Acquire::https::No-Cache "true";' 'APT::Update::Error-Mode "any";' > /etc/apt/apt.conf.d/99g08-mirror
cat /etc/apt/apt.conf.d/99g08-mirror > "$out/apt-options.txt"
source /ch14/scripts/g07_env.sh "$out"
apt-get install -y --no-install-recommends ros-jazzy-std-srvs ros-jazzy-visualization-msgs ros-jazzy-rosgraph-msgs >/dev/null
export ROS_DOMAIN_ID=101 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
stage=colcon
mkdir -p /tmp/g08_ws/src
cp -a /ch14/ros2_ws/src/ch14_rl_deployment /tmp/g08_ws/src/
(cd /tmp/g08_ws && python "$(command -v colcon)" build --packages-select ch14_rl_deployment) 2>&1 | tee "$out/colcon.log"
set +u
source /tmp/g08_ws/install/setup.bash
set -u
stage=clock_reset_actual_dds
python /ch14/scripts/g08_clock_probe.py
stage=complete
