# G06 V1 — 읽기 전용 Marker 개발 및 검수 후보
기준 d4405ebb7d65aecb9d54e3d124da6bb31d699509 / Draft PR #208. G05 V9 actual PASS를 재확인: V8/V9 ZIP SHA256 및 각 42개 내부 파일 이번 독립 검증 PASS. G05/G04 안전/record/replay 원본은 변경하지 않음.
## 현상 및 설계
기존 ch15_visualization은 G05 설치 골격으로 Marker entrypoint/launch/config가 없다. T15에는 invalid point/frame/stamp, mission/epoch 전환, replay 잔상 반례가 필요하다. TargetObservation typed 계약 및 MissionStatus/SafetyState를 구독만 한다. mock은 기존 source/kind, physical은 T11 RGBD_COLOR POSITION_ONLY, replay는 G05 실제 기록 토픽에 target이 없으므로 status 전용. 원본 헤더 보존 및 두 안정적 target ID에 DELETE, 1s lifetime. Unknown safety를 성공으로 표현하지 않는다. Clock rewind는 노드 재기동까지 차단.
## 검수
명세 T15의 10 valid sphere ADD, 라벨/ID, invalid 및 stale/epoch DELETE, replay negative, 설치 config 및 actual DDS publisher graph 검수. 이번 후보는 CI 결과 전 NOT_RUN. GUI/physical 재시험 없음. pure/actual 증거는 다음 보고서에 보존. 기존 안전 계약, Ch01–14 및 성공 PIN 보호. G06-only opt-in; G04/G05 재실행 금지.
