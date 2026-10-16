# ROS 2 Study Companion - Part 1

이 저장소는 **"ROS 2와 AI로 배우는 로봇 공학 실전 가이드"** 1장의 실습 코드를 담고 있습니다. 
Ubuntu 24.04와 ROS 2 Jazzy 환경에서 시뮬레이션 기반 프로젝트를 수행하기 위한 기초 패키지입니다.

## ? 환경 요구사항
- **OS:** Ubuntu 24.04 LTS (Noble Numbat)
- **ROS 2:** Jazzy Jalisco
- **Language:** Python 3.12+
- **Build System:** colcon

## ? 설치 및 빌드 방법

1. **워크스페이스 생성 및 소스 다운로드**
   ```bash
   mkdir -p ~/ros2_ws/src
   cd ~/ros2_ws/src
   # 이 저장소를 clone 하거나 패키지 폴더를 복사합니다.
   git clone <your-repository-url>