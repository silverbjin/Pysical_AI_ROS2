#!/usr/bin/env bash
set -euo pipefail
# Run from repository root, after sourcing only ROS Jazzy and the Ch13 install.
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-176}"
export GZ_PARTITION="${GZ_PARTITION:-ch13_13_1_verify_$$}"
python Ch13/scripts/gazebo_probe.py "$@"
