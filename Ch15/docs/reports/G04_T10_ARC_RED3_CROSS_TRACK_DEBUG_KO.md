# G04 T10 디버깅 사이클 — ARC RED3: 실제 곡선 횡오차
## 1. 실제 검수 결과
Run 45932381041, Job 140287704403, Artifact 15169266117, 소스 0df3ac348b767d0794d96d17cb1c3d8b36d8a44a. 원본 ZIP SHA256 0f33a97cc5b6a1b901420c4d7c1db8488e5ee11e3fe0bb084fa15e6a98e5540b, 53/53 내부 파일 해시 독립 검증. CPU 분리와 기존 안전 조건에서 연속 ARM 게이트 PASS(재시작0, 양쪽 ARMED sim3.68s). 실제 곡선 13.42sim s, 670 엔진 표본, active fault 없음. 정지 후 XY39.440mm >30mm, yaw .008175rad <.06rad. 직선 NOT_RUN. 엔진 COMPLETED, 원본 cap 1.0, 3/3 clean, residual PASS. 최대 엔진 표본 간격 92.04ms. 이전 RED2 startup fault가 이번에 재발하지 않았지만 CPU 분리의 일반적 인과/재현성을 주장하지 않는다.
## 2. 근본 원인 분석
실제 정지 좌표 (.139367,-.155251,-1.441825), 목표 (.178688,-.158310,-1.45). 곡선 말미 실제 tangent 오차 0.97mm, cross(안쪽) 31.88mm; 0.25/0.50/0.75/1.00/1.25/1.42rad에서 cross 7.8/15.1/20.5/25.1/28.2/31.9mm 누적. 기존 arc_command는 tangent 성분만 vx에 반영, cross는 50mm 중단 기준으로만 사용. 정지 후 추가 변위 약 7mm. 정상상태 실제 body vx .017513, vy -.001987, wz -.108618; 명령 vx .009930, 실제 vx/abs(wz) .16123m <.18m 기준. 실제 반경 부족 및 보행 횡편향을 제어기가 보상하지 못했다.
## 3. 수정 후보 및 검증 경계
V2: tangent/cross 분리, feed vx .0125, inward cross에 vx gain .25, wz gain .8. 기존 범위 vx 0..018, wz -.10..-.07, tracking 50mm/arc 30mm/final 15mm/yaw .06rad 유지. 실제 RED3 trace에 명령 변화 선형 근사(vx gain .844, yaw gain1.08)만 가한 오프라인 민감도 재생: baseline 38.947mm, 후보 23.375mm, 최대 경로 오차 33.316→23.183mm. 실제 결합 비선형 응답이나 안전성 보장이 아니다. 동일 실제 구간 한 건만 재검수. 새 regression은 cross 오차 보상 부호/제한/NaN 검증. 직선은 수정하지 않았다.
## 4. 종료 안전 관측성
원본 gateway startup trace(해시 5e7731e4d13a28b8ffea5db89a8dcb8c80f40cf7163835efcd62edd0b63c159d) 첫 fault INPUT_OR_CLOCK_TIMEOUT은 sim18.48 마지막 clock 이후, settled sim18.30 뒤에 관측됐다. 마지막 engine row에는 fault 없음, normal shutdown 요청 및 clean children. V1은 정확한 shutdown ACK wall을 기록하지 않아 shutdown 이후라고 단정하지 않는다. V2는 ACK 시각을 별도 보존하고, 최초 fault가 ACK 이후의 정상 source 종료인지 검사한다. 실제 제어 중 fault를 무시하거나 reset하지 않는다.
## 5. 교육 포인트
통합 제어는 진행 방향 오차 하나만으로 경로 추종을 보장하지 않는다. 오차를 접선과 법선으로 분해하고, 실제 계측으로 변경의 방향을 정한다. Safety admission의 성공, 곡선의 성공, 전체 미션 인수는 서로 다른 계약이다. 기존 Ch13/asset/안전 계약 변경 없음. 실제 V2 결과 pending.
