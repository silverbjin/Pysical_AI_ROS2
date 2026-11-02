# LAB 1.2 — ROS 2 Jazzy 및 Ubuntu 24.04 설치

**환경:** Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12. **현재 상태:** 재현 실습 문서 작성; 실제 ROS 2 명령 실행은 NOT_RUN.

## STEP 1. OS·Python 확인
```bash
cat /etc/os-release
uname -m
python3 --version
locale
echo "CONDA_PREFIX=$CONDA_PREFIX"
printenv AMENT_PREFIX_PATH
```

**기대:** Ubuntu 24.04 (Noble), 시스템 Python 3.12, 지원 CPU 아키텍처. Jazzy가 이미 설치되어 있으면 재설치하지 않고 STEP 3으로 이동한다. Conda는 비활성화한다.

## STEP 2. 설치 (관리자 권한과 네트워크 필요)
```bash
sudo apt update
sudo apt install -y locales software-properties-common curl
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe
curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest -o /tmp/ros-apt-release.json
python3 -m json.tool /tmp/ros-apt-release.json >/dev/null
ROS_APT_SOURCE_VERSION=$(python3 -c "import json;print(json.load(open('/tmp/ros-apt-release.json'))['tag_name'])")
UBUNTU_CODENAME=$(lsb_release -cs)
test -n "$ROS_APT_SOURCE_VERSION" || exit 1
test "$UBUNTU_CODENAME" = noble || exit 1
curl -fL --retry 3 -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/$ROS_APT_SOURCE_VERSION/ros2-apt-source_$ROS_APT_SOURCE_VERSION.$UBUNTU_CODENAME"_all.deb
test -s /tmp/ros2-apt-source.deb || exit 1
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-dev-tools
```

쉘을 닫는 `exit 1`은 보안상 실패 즉시 중단을 뜻한다. 설치 명령이 시간이 흐르며 바뀔 수 있으므로 https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html 을 확인한다.

## STEP 3. ROS 환경 등록 및 확인
```bash
source /opt/ros/jazzy/setup.bash
grep -Fqx 'source /opt/ros/jazzy/setup.bash' ~/.bashrc || echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo "ROS_DISTRO=$ROS_DISTRO"
command -v ros2
command -v colcon
python3 -c "import rclpy; print(rclpy.__file__)"
```

## STEP 4. 독립 터미널 통신
터미널 A `ros2 run demo_nodes_cpp talker`, 터미널 B `ros2 run demo_nodes_py listener`. 두 셸에서 각각 Jazzy setup을 다시 source한다. **ACCEPT:** Publishing/I heard 3쌍 이상, 버전·로그 증거 보존. **NOT_RUN:** 여기서 OS 설치·WSLg·Gazebo·MuJoCo 실행 검증.

## 장애 처리
`ros2`를 찾지 못하면 source, `rclpy` 실패 시 Python 환경 충돌, listener 무응답 시 양측 `ROS_DOMAIN_ID`·RMW·방화벽 설정을 검사. GPU 시뮬레이터는 별도의 렌더링 시험으로 확인한다.

## Evidence 기록

| 항목 | 실제 출력·환경 | 판정 |
|---|---|---|
| `git rev-parse HEAD` / `ros2 doctor --report` | 기록 필요 | NOT_RUN |
| 각 STEP의 실제 종료 코드·노드/토픽 로그 | 기록 필요 | NOT_RUN |
| 실패 증상, 변경 사항 및 재실행 | 기록 필요 | NOT_RUN |

[절별 리뷰](SECTION_1_2_REPORT_KO.md) 참조.
