# LAB 1.1 — 로봇 개발의 패러다임 변화

**환경:** Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12. **현재 상태:** 재현 실습 문서 작성; 실제 ROS 2 명령 실행은 NOT_RUN.

## 준비
1.2절의 Ubuntu 24.04/ROS 2 Jazzy 설치가 선행되어야 한다. 새 셸에서 아래 명령을 실행한다.

### 터미널 A — Publisher
```bash
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_cpp talker
```

### 터미널 B — Subscriber
```bash
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_py listener
```

### 터미널 C — 분산 그래프·QoS 확인
```bash
source /opt/ros/jazzy/setup.bash
ros2 node list
ros2 topic list -t
ros2 topic info -v /chatter
ros2 interface show std_msgs/msg/String
ros2 topic echo /chatter
```

## 관찰 포인트
- C++ talker와 Python listener의 번호가 3회 이상 일치하는가? 표준적으로 `roscore` 없이 DDS discovery가 작동하는가?
- `ros2 topic info -v`에서 publish/subscribe endpoint 수와 reliability·durability·history/depth를 읽는다.
- ROS 2 CLI 데몬은 ROS 1 마스터와 동일한 중앙 데이터 중개자가 아니다.
- Quality-of-Service는 호환성 정책이기도 하다. RELIABLE 요청 subscriber는 BEST_EFFORT 제공 publisher와 연결되지 않을 수 있다. 이 실습은 packet-loss 성능 검증이 아니다.

## 교육용 응용·합격
원고의 서빙 로봇에서 LiDAR, 모터 명령에 각기 다른 QoS 정책이 필요한 이유를 작성한다. **ACCEPT 조건:** Jazzy 확인·talker/listener 3회 통신·노드 2개·`/chatter` 타입 및 QoS 출력 확인. **NOT_RUN:** ROS 1 마스터 장애 실험, SROS2 암호화, Zero-copy 성능, 실물 하드웨어.

## Evidence 기록

| 항목 | 실제 출력·환경 | 판정 |
|---|---|---|
| `git rev-parse HEAD` / `ros2 doctor --report` | 기록 필요 | NOT_RUN |
| 각 STEP의 실제 종료 코드·노드/토픽 로그 | 기록 필요 | NOT_RUN |
| 실패 증상, 변경 사항 및 재실행 | 기록 필요 | NOT_RUN |

[절별 리뷰](SECTION_1_1_REPORT_KO.md) 참조.
