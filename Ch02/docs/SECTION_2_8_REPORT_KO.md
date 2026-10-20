# SECTION 2.8 ROS 2 QoS 코드 리뷰 및 비교 실습 보고서

- **원고 범위** 2.8.1~2.8.4 / **기준** `main@94264bee4b53ce4c9676011b98e72368b1e40690` / 2026-10-20.
- **대상** `qos_test_node.py`, `setup.py`, 새 `qos_compare_subscriber.py`.
- **상태**: source 단에서 호환성 실습 공백 보완. 실제 DDS/RMW 동작·연결 테스트 미검증.

## 문제와 수정

| ID | 등급 | 진단 | 개선 |
|---|---|---|---|
| 2.8-01 | Medium / 실습 부족 | 기존 `qos_test_node.py`에는 BEST_EFFORT publisher만 있고 subscription 코드는 주석. 원고의 compatibility 표를 실제 검증할 짝이 없음 | 독립 `qos_compare_subscriber.py` 추가. parameter `reliability`로 `reliable` 또는 `best_effort` 선택 |
| 2.8-02 | Medium | CLI default subscription QoS는 ROS 배포판/명령 설정에 따라 달라 해설만으로 호환성 실패 재현이 불명확 | 명시적 프로파일 구독자 2종을 통한 재현 절차 마련 |
| 2.8-03 | Medium | 원고의 Reliable는 “데이터가 반드시 도착한다”는 무조건적 표현이며 DDS QoS는 모든 장애 상황의 절대적 전달 보증이 아님 | 내구성/재전송/실패 조건으로 설명 |
| 2.8-04 | Medium | 원고의 “로봇 상태엔 reliable, transient local”은 요구 조건에 따른 설계 선택이며 모든 경우 권고로 일반화할 수 없음 | 센서 latency, 새 구독자 replay, publisher 생존 조건을 분리 |
| 2.8-05 | Low | deadline/liveliness 정의만 있고 실제 이벤트 콜백·정지 증거 실습 없음 | 2.8.4는 설명 범위, 구현·안전 인터록 검증 미포함 |
| 2.8-06 | **선행** | `std_msgs` import 의존성 누락 | **2.3절 브랜치의 package.xml 변경에 포함**. 2.3 PR 선행 병합 필요 |

## 변경
- **추가** `my_robot_system/qos_compare_subscriber.py` — 문자열 수신, reliability 파라미터·검증, 수명 정리.
- **수정** `my_robot_system/setup.py` — `qos_compare_sub` console_script 등록.
- **유지** `qos_test_node.py` — 기존 BEST_EFFORT / KEEP_LAST 1 / VOLATILE publisher 그대로 유지.

## 검증 표

| 항목 | 현재 결과 |
|---|---|
| 원본 publisher QoS 정책·타이머 정적 확인 | PASS(정적) |
| 새 subscriber reliability 프로파일·콘솔 매핑 | PASS(정적) |
| ROS 2 빌드 및 rclpy import | NOT RUN |
| RELIABLE 구독자 무수신과 QoS incompatibility 경고 | NOT RUN |
| BEST_EFFORT 구독자 수신 | NOT RUN |
| deadline/liveliness 이벤트 실제 관찰 | NOT RUN (실습 범위 밖) |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
# A: ros2 run my_robot_system qos_test_node
# B (mismatch):
ros2 run my_robot_system qos_compare_sub --ros-args -p reliability:=reliable
# B 종료 후 다시:
ros2 run my_robot_system qos_compare_sub --ros-args -p reliability:=best_effort
```

A에서 1Hz 발행 로그가 보이는 것과 B에서 실제로 message를 받는 것은 **서로 다른 확인 항목**이다. 2.3절 manifest 변경, 2.5절 action_msgs 수정 적용 후 runtime 확인. 실측 QoS 이벤트 로그 없이 절대 성공으로 선언하지 않음.

참고: ROS 2 공식 QoS compatibility 및 `rclpy.qos` 정책 정의.
