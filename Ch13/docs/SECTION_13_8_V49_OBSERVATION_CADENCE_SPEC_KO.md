# v49 원본 처리율 복원과 저장 deadline 재현 명세

정상 완주 기준 유지·Owner 인수 보류. v48 실제 사례는 최종 이동11.311mm/정착/find/팔 준비를 통과했으나 PRE_GRASP 중 OBSERVATION_EXPIRED로 실패했다. 촬영 요청 전 Scan 지연은 제거된 것을 기록으로 확인했다. 해당 사용 관측의 최초 나이는302.381ms였다.

다음 capture67808000000은8757.229389063에 촬영됐고 네 native/receipt 결합은 약8757.273662까지 도착했다. 직전 inference 시작8757.212981876이므로10Hz에서는8757.312982 전 처리가 제한되고 실제 시작8757.329831725/종료8757.354383926이었다. 직전 관측 만료8757.346126638 뒤다. 15Hz라면8757.279649부터 처리할 수 있다. 기존13.7/13.8이 지원하는15Hz를 재사용해 이 대기 조건을 작은 실제 ROS fixture에서 재현한다. 15Hz는 일반적인 공식 안전 보증값이 아니라 이 패키지의 기존 지원 처리율이다. ROS2 Jazzy 단일 executor 동작 및 현재 native callback trace를 근거로 하며 새 executor를 도입하지 않는다.

v42의 과거15Hz 실패는 보존한다. 당시와 달리 v47은 첫 callback import를 제거했고 v48은 Scan 이전에 불변 snapshot을 제출한다. 처리율 복원만으로 모든 지연이 해결된다고 하지 않고 전체 조건을 새 source로 검증한다.

1. RED: v48 원본 capture/receipt/inference/deadline 수치를 넣은 실제 VisionObserver fixture에서 Scenario.vision_hz로 새 관측을 제때 처리하도록 기대한다.10Hz의 불필요한 대기에서 실패를 확인한다. 기존 portable 처리율 계약도15Hz 기대를 먼저 반영한다.
2. GREEN: Level2의10Hz 특례를 제거해 기존15Hz로 복원한다. 모델·geometry·QoS·framecache·300ms/TF100ms·timestamp·단일 owner·제어는 유지한다. 새 관측은 원래 수명 내에 처리되어야 하며 기존 관측의 시각을 바꾸지 않는다.
3. REFACTOR/자체 REVIEW/관련 및 전체 시험/COMMIT/공개 CI 실제 runner/steps 확인을 수행한다.
4. 새 freeze/build/audit/runtime 일치 후15Hz/overlap1/전진DUBIN+RPP/계측1의 새 UUID로 실제 검증한다. CPU와 최초 실패·종료를 기록한다. 목표 시간120sim초와 나머지 원래 성공 수치를 유지한다. v48 PRE_GRASP 후보67.234sim초는 전체 시간 목표에 부담이 되는 별도 관측이며 이번 처리율 수정과 함께 팔 속도/경로를 바꾸지 않는다.
5. 연속 정상 성공 후 정식 평가/가이드/Owner 인수로 진행한다. 부품 통과나 서로 다른 사례의 부분 통과를 정상 연속 성공으로 합치지 않는다.
