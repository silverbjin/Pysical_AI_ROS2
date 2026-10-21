# 10.6절 코드 리뷰 보고서 — 페이싱·바운딩·크롤 및 전이

- 작성/정적 검토: 2026-10-21 KST
- 원고 범위: 첨부 『Physical AI 실무 가이드』 10.6절
- 소스 기준: `silverbjin/Pysical_AI_ROS2` main (작업 시작 `bab76f6ca7df0bda6efd8882c1a698561707e51d`)
- 파일: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/generalized_gait_planner.py`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_controllerFSM.py`; `Ch10/ros2_ws/src/my_robot_interfaces/srv/SetGait.srv`
- 평가: **정적 리뷰 수행, 실제 ROS 2/Gazebo 빌드 및 물리 보행 성공 여부 미검증; 통합 판정 보류**

## 학습 목표와 실제 코드의 차이

trot/pace/bound/crawl의 위상 배열과 duty, frequency를 테이블로 관찰하고 '요청됨'과 '전환 적용됨'을 구별한다. 서비스 방식은 원고에 제안되어 있지만 현재 작동하는 서비스 서버는 확인되지 않는다.

## 문제 목록 및 권고 조치

| 우선순위 | 코드 문제 | 근거·영향 | 권고 |
|---|---|---|---|
| HIGH | 서비스 정의만으로는 서비스를 호출할 수 없음 | `SetGait.srv`가 저장소에 존재하지만 현행 `trot_controllerFSM.py`와 `quadruped_controller_ros2.py`에는 `create_service(SetGait, 'set_gait', ...)` 구현이 없다. | `ros2 service list -t`로 부재 확인 후 서비스 서버 구현/테스트. |
| HIGH | 원고와 GAIT_LIBRARY의 crawl 오프셋 불일치 | 원고 10.6은 `crawl=[0.75,0.25,0.5,0.0]`을 예시로 쓰지만 실제 `generalized_gait_planner.py`는 `[0.0,0.5,0.25,0.75]`을 사용한다. | 실제 다리 순서 FL/FR/RL/RR과 접지 안정성 기준으로 한 세트를 선택하여 원고와 통일. |
| HIGH | 전이와 파라미터 변경의 연속성 미검증 | planner는 주기 종료시 `next_gait`를 바꾸지만 기하학적 궤적은 새 duty와 frequency에 대해 이어붙이기/착지 확인을 하지 않는다. | 전후 발끝 위치/속도·접촉 플래그를 비교하고 불연속 시 보간·중립 자세 경유. |
| MEDIUM | 공유 객체 변형 및 큰 dt 처리 | `GAIT_LIBRARY`는 `GaitConfig` 객체를 공유하고 FSM `_sync_controller_params`가 그 객체의 frequency를 직접 덮어쓴다. `update()`는 한 주기만 감산한다. | 인스턴스별 config 복사·dt modulo/다중 주기 처리와 reset 추가. |
| MEDIUM | 지원 gait 목록이 컨트롤러 간 불일치 | GeneralizedGaitPlanner는 trot, pace, bound, crawl만 제공하지만 `quadruped_controller_ros2.py`의 supported_gaits에는 walk가 존재한다. | 하나의 gait registry로 UI·서비스·모듈을 일원화. |

## 확인한 내용과 확인하지 못한 내용

- **확인:** 현재 main의 관련 Python, launch, XML/YAML 소스와 사용자 제공 원고를 대조했다. 결함 지적은 텍스트/실제 코드의 특정 표현을 근거로 한다.
- **확인 불가:** 해당 작업 환경에서 실제 WSL2 ROS 2 Jazzy·Gazebo Harmonic 실기동, colcon 컴파일, 센서·토픽 왕복, 지면 접촉·낙상 로그는 수집하지 않았다.
- **혼동 금지:** 명령/상태 메시지가 발행된 사실은 발의 실제 움직임 또는 물리적 전진 성공을 의미하지 않는다.
- **변경 범위:** 이 PR은 분석 문서와 실습 가이드만 추가한다. 실패 원인이 있는 소스 코드는 수정하지 않았다.

## 재현 권장 순서

```bash
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
```

## 재현 및 승인 체크리스트

1. [ ] 4개 gait의 위상·동시 스윙 다리 조합을 확인한다.
2. [ ] 전환 요청 직후와 주기 완료 이후 활성 gait가 다른지 확인한다.
3. [ ] `set_gait` 서비스가 없다면 호출 성공으로 기록하지 않고 미구현으로 표시한다.
4. [ ] 해당 실행 환경(WSL2, ROS/Gazebo 배포판, Git SHA, 의존성) 기록
5. [ ] 실패/수정 전후의 테스트 로그 및 시뮬레이션 증거 저장
6. [ ] 10.1~10.7 선행 위험의 해결 여부 확인

**최종 의견:** 안전성과 재현성을 입증하는 실제 테스트 이전에는 '동작 완료/성공'으로 판정하지 않는다. 자세한 교육 절차는 [LAB_10_6_GUIDE_KO.md](LAB_10_6_GUIDE_KO.md) 참조.
