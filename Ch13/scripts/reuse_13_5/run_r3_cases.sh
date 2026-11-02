#!/usr/bin/env bash
set -e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
echo "START obstacle 05c9c5ca-1b7d-47a2-a380-cdc390a092e5"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/run_navigation.sh" obstacle "$reuse_repo/Ch13/evidence/section_13_5_reuse/05c9c5ca-1b7d-47a2-a380-cdc390a092e5"
echo "PASS obstacle 05c9c5ca-1b7d-47a2-a380-cdc390a092e5"
echo "START blocked 535013f5-7288-4b71-afe7-b29aaed0a164"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/run_navigation.sh" blocked "$reuse_repo/Ch13/evidence/section_13_5_reuse/535013f5-7288-4b71-afe7-b29aaed0a164"
echo "PASS blocked 535013f5-7288-4b71-afe7-b29aaed0a164"
echo "START cancel b129a641-745c-4445-bc40-b5459d62a527"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/run_navigation.sh" cancel "$reuse_repo/Ch13/evidence/section_13_5_reuse/b129a641-745c-4445-bc40-b5459d62a527"
echo "PASS cancel b129a641-745c-4445-bc40-b5459d62a527"
