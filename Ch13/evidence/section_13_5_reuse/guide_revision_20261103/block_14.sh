# 터미널 B, 실행 중: 실제 body의 상대 높이·회전 확인
source "$HOME/physicalai_13_5/lab_env.sh"
timeout 5s ros2 run tf2_ros tf2_echo reuse/nav_base reuse/base
