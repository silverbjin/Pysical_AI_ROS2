# Ch09 — 4족 보행 로봇 모델링 (ROS 2 Jazzy · Gazebo Harmonic)

> 첨부 원고 9장에 대응하는 코드와 실습 문서 모음. 9.1~9.8절의 **정적 코드 리뷰 보고서**와 **따라하기 가이드**를 분리한다. 리뷰만 수행한 상태에서는 Gazebo 정상 구동을 보증하지 않는다.

| 절 | 내용 | 실습 | 코드 리뷰 |
|---|---|---|---|

| 9.1 | 12자유도 기구 구조 | [실습](docs/LAB_9_1_GUIDE_KO.md) | [리뷰](docs/SECTION_9_1_REPORT_KO.md) |
| 9.2 | Xacro 매크로 | [실습](docs/LAB_9_2_GUIDE_KO.md) | [리뷰](docs/SECTION_9_2_REPORT_KO.md) |
| 9.3 | 관성·충돌 | [실습](docs/LAB_9_3_GUIDE_KO.md) | [리뷰](docs/SECTION_9_3_REPORT_KO.md) |
| 9.4 | Gazebo·브리지 | [실습](docs/LAB_9_4_GUIDE_KO.md) | [리뷰](docs/SECTION_9_4_REPORT_KO.md) |
| 9.5 | 론치·스폰·TF | [실습](docs/LAB_9_5_GUIDE_KO.md) | [리뷰](docs/SECTION_9_5_REPORT_KO.md) |
| 9.6 | P/I/D 기립 | [실습](docs/LAB_9_6_GUIDE_KO.md) | [리뷰](docs/SECTION_9_6_REPORT_KO.md) |
| 9.7 | 단일 다리 명령 | [실습](docs/LAB_9_7_GUIDE_KO.md) | [리뷰](docs/SECTION_9_7_REPORT_KO.md) |
| 9.8 | QA·트러블슈팅 | [실습](docs/LAB_9_8_GUIDE_KO.md) | [리뷰](docs/SECTION_9_8_REPORT_KO.md) |

> **병합 주의:** 이 README는 9.8절 PR에만 추가했다. 앞선 독립 PR(9.1~9.7)의 문서가 main에 병합되기 전에는 일부 링크가 아직 존재하지 않을 수 있다. 권장 병합 순서는 9.1→9.8이다.

## 처음 시작하기

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
ros2 launch my_quadruped_bot simulation.launch.py
```

다른 장(Ch10·Ch11 등)의 `my_quadruped_bot`이 overlay에 있으면 다른 모델이 실행된다. prefix가 Ch09 install을 가리키는지 먼저 확인한다. 스폰이 되더라도 use_sim_time, RViz launch 경로, 제어 퍼블리셔 중복 같은 알려진 문제가 있으므로 **각 절 리뷰의 차단 요인을 읽고 실행**한다.

9장의 목표는 모델 전개 → 물리 속성 검증 → 통신 → 기립 → 1개 관절 궤적 → QA다. Ch10 강화 보행으로 넘어가기 전에는 관절 영점·부호·순서와 TF·제어 소유권을 검증해야 한다.

**검증 범위:** 2026-10-21 기준 원격 main 소스 정적 리뷰. ROS/Gazebo GUI 물리 런타임 및 `colcon test`는 NOT_RUN; 이후 실습에서 실제 검증 증거를 추가해야 한다.
