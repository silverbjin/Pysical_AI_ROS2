#!/usr/bin/env bash
# Optional unprivileged alternative to apt install, scoped to the 13.7 build.
set -eo pipefail
bt_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bt_build=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_7_build}
/usr/bin/python3 "$bt_scripts/../../ros2_ws/src/ch13_mission_orchestration/ch13_mission_orchestration/tools.py" "$bt_build"
mkdir -p "$bt_build/bt_deps"
cd "$bt_build/bt_deps"
apt download ros-jazzy-py-trees=2.6.0-1noble.20260911.044440 \
 ros-jazzy-py-trees-ros=2.6.0-1noble.20261006.034533 \
 ros-jazzy-py-trees-ros-interfaces=2.1.2-1noble.20260911.113643 \
 python3-pydot=1.4.2-2 python3-pyparsing=3.1.1-1
sha256sum -c <<'HASHES'
70b3b3f0188823ec8823d138fa2b45f984f5e12cb48a16ab1de0ca7a474627f5  ros-jazzy-py-trees_2.6.0-1noble.20260911.044440_amd64.deb
ad720943b8e008ea4c1bbf5b57926576b2dffd8e046b65875b0a85f41f7b4489  ros-jazzy-py-trees-ros_2.6.0-1noble.20261006.034533_amd64.deb
7efb8737c16f719c587c45bf634a673f23eea7375c0bff74c7a0faea28238876  ros-jazzy-py-trees-ros-interfaces_2.1.2-1noble.20260911.113643_amd64.deb
6d212d8cce24cfea0a5c976739a3505c0de562c080c24bdd79344333d11fcbf1  python3-pydot_1.4.2-2_all.deb
ec2395b1fe34a7a828f5cfabc4262217f6a86fb6ecb993fc18fbad3fc9edabba  python3-pyparsing_3.1.1-1_all.deb
HASHES
for bt_file in ros-jazzy-py-trees_*.deb ros-jazzy-py-trees-ros_*.deb ros-jazzy-py-trees-ros-interfaces_*.deb python3-pydot_*.deb python3-pyparsing_*.deb; do
 dpkg-deb -x "$bt_file" root
done
sha256sum *.deb > deb_sha256.txt
