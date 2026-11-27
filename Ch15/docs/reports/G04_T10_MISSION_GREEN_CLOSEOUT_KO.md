# G04 T10 최종 인수 및 교육용 회고 — 실제 BT·MCAP GREEN

## 1. 판정 및 고정 실행 기준

- G04: PASS_SCOPED_CH15_BASIC_V6_AND_T11.
- 실제 T10 Ch15 대체 basic 프로파일: PASS. 원본 CH13_NATIVE RED4 실패는 보존한다. full pick/return/place 및 WSL2 L3는 인수하지 않는다.
- 실행 SHA: `de16542fbb4d7aae1876fd39fd782cfcf77f655b`, 기준 main `1931cac92585fc155357880b584c72c76d67257c`.
- [CI 45943468828](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45943468828), job 140322747814, artifact 15174240698. Job 종료 success 확인.
- ZIP 4,934,574 bytes, SHA256 `3cac86552c9e62544251d507b189533d26c69254046cfee574069ea9ff915147`, 내부 75/75 해시 독립 검증.
- 원본 407 source/94 assets freeze 및 모델 SHA 보존. Ch13 수정 없음. main merge 및 외부 모델/MCAP raw 배포 HOLD.

## 2. 정량 인수 결과

| 계층 | 결과 | 실제 증거 |
|---|---|---|
| 기존 basic assessor | 10/10 PASS | motion_observation, terminal, no_manipulation, worker, goals, engine, children, recording, telemetry, world |
| Ch15 구간 계약 | 16/16 PASS | 절대 목표, 지도/entry, arc/straight, 재관측, IK, 단일 명령, 세션, GC, 종료 |
| 독립 엔진 | 5/5 PASS | 동일 모델, force cap, clean engine, arc, straight |
| 독립 ZIP/영수증 | 22/22 PASS | 실제 엔진 및 BT/MCAP 영수증 대조 |
| 곡선 정지 | PASS | 13.210966mm / .006682224rad, 693 samples, 기준 30mm/.06rad |
| 직선 최종 정지 | PASS | .577126mm / .020186836rad, 232 samples, 기준 15mm/.06rad |
| 실제 BT | SUCCESS | navigate → find → finish, 967 ticks, 동일 session |
| MCAP | 9/9 PASS | 15개 exact topics, 46,345 messages, 정상 close |
| 실제 세계 | PASS | ramp 접촉 223.537N, live cost 80/80, fresh RGB-D/IK |
| 안전 종료 | PASS | 11/11 children exit, residual free, worker join/exit0, telemetry 967/0 errors |

ROS pose와 독립 엔진 pose 차이 0m/0rad, 시각 오차 1ns 미만. 기존 속도 한계, 정지 허용 오차 및 100ms 신선도 제한 유지. 엔진 70.540 sim s / 100.461 wall s, 3,527 observations. 실제 arm/gripper 명령 0. GC 수집 [632,57,0], 원래 정책 복원, peak RSS 1,409,668 KiB (약 1.344GiB). 종료 ACK 후 318.116ms에 gateway INPUT_OR_CLOCK_TIMEOUT 기록; 운전 중 fault가 아니며 숨기지 않는다. Navigation fault 없음.

## 3. 디버깅 교육용 비교

| 단계 | 실제 실패 경계 | 변경 및 검증 |
|---|---|---|
| Native RED4 | RR_calf/table leg 접촉 | 원본 실패 보존, geometry→plant identification |
| ARC RED1/2 | startup/미래 stamp | CPU affinity, stable prearm/trace, 안전 제한 유지 |
| ARC RED3/4 | cross-track, stop slip | 측정 기반 arc radial 및 straight 보상; 독립 V3 GREEN |
| Table RED1 | 카메라 시야 밖 | 실제 고정 월드 투영/재관측, costmap freshness |
| Table RED2 | DDS startup | 이미 확인한 startup 원인 개선 재사용 |
| Table RED3 | GC와 상태 공백 일치 | engine-only Gen2 지연/복원, 메모리 게이트 |
| Table RED4 | 최종 24.301mm/.062501rad | 두 실제 arc 횡편향에 근거하여 arc 참조만 +20mm, 최종 목표 불변 |
| Table GREEN | 4.990mm/.036602rad | 실제 식탁 구간 15/15; BT/MCAP은 별도 |
| Mission RED1 | arc settled 30.312mm >30mm | 네 실제 trace 민감도 분석, 식탁 전용 cross-forward gain .25→.45; 원본 V3 불변 |
| Mission GREEN | 실제 BT·MCAP 끝까지 PASS | 10/10 + 16/16 + 독립 22/22; 성공 후 중복 물리 재실행 금지 |

핵심 교훈: 최초 실패 경계와 후속 오류를 구분한다. 오프라인 proxy는 후보 선정이지 실제 PASS가 아니다. 앞 구간의 합격이 뒤 구간의 합격을 보장하지 않으며, 정지 이후 실제 좌표로 평가한다. 편향 보정은 이 월드의 측정에 근거한 경험적 설계로 범용 보행기 성능을 보장하지 않는다.

## 4. MCAP 검수 및 재현

CI에서 raw MCAP을 직접 읽어 메시지별 검수 9/9를 수행했다. 43,566,540 bytes, SHA256 `c1d4cfc44a0e943cf8b57a39efd44d0319f05702be3697600360d59494b74121`. 시작 3.52s → 최초 motion 3.68s → 마지막 motion 69.52s → SUCCESS 70.54s. 공개 artifact는 payload receipt, metadata 및 기록 판정만 포함하며 raw MCAP은 포함하지 않는다. 따라서 독립 검수는 공개 영수증과 metadata 일치 및 엔진 원본 재계산이며 raw MCAP 재열람이라고 주장하지 않는다.

```bash
# Ch15/scripts 디렉터리에서, 원본 CI ZIP 내려받은 뒤 (Python + PyYAML)
python audit_table_l2_artifact.py /path/to/t10-mission-green.zip --sha256 3cac86552c9e62544251d507b189533d26c69254046cfee574069ea9ff915147
```
독립 auditor를 실제 GREEN에서 exit0, 실제 RED1에서 FAIL, 단독 table GREEN에서 NOT_RUN으로 검증했다. 별도 검수 코드 및 [정량 receipt](../../evidence/g04/t10_mission_green_receipt.json) 보존.

## 5. G04 종료 범위 / 인계

T11 기존 실제 Harmonic run 45910585983 (artifact 15160425409): 정상 10/10, 최대 오차 2.045876541mm, IoU 최소 .9216202813, stamp skew 0ns, invalid depth 3/3 및 실제 occlusion 3/3 차단, command publisher 0, 정상 종료. 이미 확보한 증거를 재사용한다.

G04 Ch15 대체 basic T10 및 T11 실제 검수 완료. 원본 CH13_NATIVE RED4 FAIL 별도 유지, 원본 native 교체 성공이라고 표현하지 않는다. Full manipulation 및 L3 NOT_RUN. G05~G09 NOT_STARTED; 다음 개발은 별도 지시 시 진행. Draft PR #208 유지, main 미병합. 성공한 물리 CI를 반복하지 않는다.
