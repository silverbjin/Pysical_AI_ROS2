# v48 촬영 요청 전 생산 지연 보완 명세

기준 v47/35de775e. 정상 완주 기준 유지·Owner 인수 보류. v47 실제 UUID a581a30c-3a1a-45da-9392-709c21df9044는 survey 이후 VISION_EXPIRED로 실패했다. 최초 관측 나이315.002ms, 다음 건강 관측은 직전 촬영300ms 만료보다17.036ms 늦었다. 관측 callback은 해당 구간 최대17.083ms였고 모듈 초기화 지연과 다른 계열이다.

같은 source의 실제 생산 로그에서 직전 state publish88.070ms, 다음 촬영까지170.024ms, 다음 촬영 요청 이전 Scan42.013ms가 있었다. 기존 overlap1은 촬영 요청을 state publish보다 먼저 보내지만 Scan 뒤에 보낸다. 상태 시각을 늦게 치환하지 않고 이미 획득한 불변 qpos snapshot을 Scan보다 먼저 기존 renderer에 제출하는 최소 변경을 검사한다. 다른 지연이 동일하면42ms의 전송 대기를 제거할 수 있다는 가설이며 실제 성공 보증은 아니다.

공식 설치 버전 MuJoCo3.13.0 Python 문서는 배열이 내부 메모리를 직접 보며 이후 step이 이를 수정하므로 필요한 시점에 복사해야 함을 설명한다. 기존 CameraWorker의 immutable snapshot 패턴을 유지한다: https://github.com/google-deepmind/mujoco/blob/3.13.0/doc/python.rst . 새 렌더러/프로세스/시계/driver는 추가하지 않는다.

1. RED: 저장 실패의 Scan42ms/state88ms 지연을 작은 clock fixture로 재현한다. overlap1에서는 원본 qpos copy와 capture stamp/wall을 그대로 유지한 채 Scan 전에 제출하도록 기대하고 실패를 확인한다. 기본 overlap0 순서는 유지한다.
2. GREEN: SensorSuite.step의 기존 opt-in 요청 순서만 바꾼다. Scan 자체·메시지·빈도·TF·state publish·action·policy·PD·안전 판정은 유지한다. capture/scan 시간을 별도 측정한다.
3. REFACTOR/자체 REVIEW/관련 및 전체 시험/COMMIT/공개 CI 실제 step 확인을 수행한다. 생산 로그의 다른 중복 publish 등은 이 작업에 함께 수정하지 않는다.
4. 새 freeze/build/audit/runtime 일치를 확인하고 같은10Hz/overlap1/전진DUBIN+RPP/계측1의 새 UUID 단일 실제 사례를 실행한다. 실패는 최초 경계와 정상/비정상 종료를 구분해 보존한다. 원래300ms/TF100ms/최종3cm·120sim초·높이20mm 목표를 완화하지 않는다.
5. 연속 파지·운반·놓기 실제 성공 후에만 정식10회 평가와 최종 Owner 인수로 넘어간다. 앞선 한 번의 이동 통과나 이번 부품 개선을 완주로 표시하지 않는다.
