# SECTION 3.1 — URDF 기초 모델 코드 리뷰·검증 보고서

- **원고 범위**: 3.1.1 URDF, 3.1.2 link/joint, 3.1.3 `simple_arm.urdf`
- **기준**: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 검토일 2026-10-20 KST
- **대상**: `Ch03/ros2_ws/src/my_robot_description/urdf/simple_arm.urdf`
- **판정**: **정적 수정 완료 / ROS 2 실행 검증 대기(PENDING_RUNTIME_VERIFICATION)**

## 1. 코드와 원고 대조
원고의 축약된 `<link name="link1">` 설명과 달리 GitHub 파일에는 link1의 visual/collision/inertial이 구현돼 있다. 2개 링크와 1개 회전 관절을 구성하는 **1-DOF 기초 모델**이다. 3.2절의 2-DOF 모델과 혼동하지 않는다. `joint1`은 Z축 회전이고 범위는 -1.57~+1.57 rad이다.

## 2. 발견 사항
| ID | 심각도 | 근거 | 처리 |
|---|---|---|---|
| 3.1-01 | Medium | base의 visual/collision 중심은 Z=0.025m인데 관성 중심 `inertial/origin` 누락 | Z=0.025m 명시 |
| 3.1-02 | Medium | link1 길이 0.3m의 질량 중심은 Z=0.15m이나 관성 중심 누락 | Z=0.15m 명시 |
| 3.1-03 | Medium | 기존 관성 대각값은 기하형상과 무관한 예시 상수 | 균질 원기둥·직육면체 공식으로 근사 |
| 3.1-04 | Info | 원고는 단순 링크 예시 일부만 제시 | 원고와 저장소 실습 파일의 범위 차이를 가이드에 명시 |

근사 계산: 원통 `Ixx=Iyy=m(3r²+h²)/12`, `Izz=mr²/2`; 상자 `Ixx=m(y²+z²)/12`, `Iyy=m(x²+z²)/12`, `Izz=m(x²+y²)/12`. 강체의 실제 질량분포를 측정한 값은 아니다.

## 3. 정적 검증
- **PASS (소스 대조)**: `joint1`의 parent=`base_link`, child=`link1`; link 이름 중복 없음.
- **PASS (수식 대조)**: base (m=5, r=0.1, h=0.05) 및 link1 (m=1, 크기 0.05×0.05×0.3)의 관성 대각값이 물리 근사 공식과 일치.
- **미수행**: 이 실행 환경에는 `check_urdf`, `ros2`, `colcon`, RViz/Gazebo가 없어서 XML 파서/URDF 파서 실제 결과 및 물리 시뮬레이션을 PASS로 간주할 수 없다.

## 4. 독자 재현 명령
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt install -y liburdfdom-tools ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher-gui ros-jazzy-rviz2
check_urdf src/my_robot_description/urdf/simple_arm.urdf
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description display.launch.py model:=simple_arm.urdf
```
`display.launch.py model:=...` 인자 선택은 **3.1절 브랜치만으로는 지원하지 않으며** 3.2절에서 수정된 런치 파일 병합 후 사용한다. 선행 병합 전에는 3.2절 런치 패치 없이 수동 파서 검증까지만 수행한다.

## 5. PR 승인 조건
`check_urdf` 종료코드 0, RViz에서 링크 2개/회전 조인트 1개, 슬라이더 -1.57~+1.57rad 관찰, 실행 로그 및 스크린샷 저장. **현재 런타임 Acceptance는 보류**.
