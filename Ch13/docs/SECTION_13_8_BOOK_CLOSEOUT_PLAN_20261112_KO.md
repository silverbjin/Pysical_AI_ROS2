# 조정 목표에 따른 13.8 교재 패키지 마무리 명세·계획

2026-11-12. 사용자가 다음 제공 범위를 확정했다: 기본 실습은 이동·관측·상태 확인·안전 종료·실패 판독, Level2 확장 시연은 과거 운반·놓기 기록 해설, 최신 연속 임무와 Level3 파지 이후는 향후 과제다. 전체 미션 성능/성공률 달성이 이번 완료 조건은 아니다. Level3 충돌 튜닝3회 소진·중단은 유지한다. 단일 작업자로 진행한다.

## 확정 구현 범위

기존 run_mission.py에 명시적 `--exercise basic`을 추가한다. 기존 full 기본값과 과거 실행 의미는 유지하고 학생용 시작 가이드는 basic 명령만 사용한다. basic BT는 navigate→find→finish이며 pick/return/place를 요청하지 않는다. 원래 관측·실제 정착·단일 owner·안전/취소·공유lock/종료 절차는 그대로다. 같은 기존 worker의 opt-in observation_only 경계로 파지 handoff와 MoveIt 기동을 생략한다. 팔/gripper 명령을 발행하지 않는다. 로봇의 원래 native hold/보행 정책은 유지한다.

결과는 `basic_result.json`으로 기록한다. 기본 실습의 이동·관측 완료와 전체 임무 성공을 혼동하지 않도록 full의 trial.json과 분리한다. 오류/취소를 성공으로 만들지 않으며 동작 단계와 종료/잔여를 각각 판독한다. 실습 중 실패도 원인·중단·회수 기록을 학습 자료로 제출할 수 있지만 이동·관측 PASS와 구분한다.

새 읽기 전용 inspect_case.py는 보존된 basic_result 또는 원래 trial/BT/물리 판정을 요약한다. 원본 verdict를 덮어쓰거나 archive를 live 권한으로 사용하지 않는다. Level2 v28 전체 순서1회와 현재 코드의 실제 인수는 구분한다.

## 순차 실행 및 검증

- [ ] 기존 공식 py_trees의 tree child 제거/순차 실행 패턴과 기존 Session/worker/종료 경계를 확인한다. 새 executor나 정책을 만들지 않는다.
- [ ] RED: 실제 BT/TaskPort에서 basic이 pick/return/place를 요청하지 않고 Find 이후Finish로 가는 계약, no-op handoff, 결과 분리/종료 판독, 읽기 전용 요약의 핵심 동작을 시험한다.
- [ ] GREEN: 최소 opt-in hook과 basic 결과/판독기를 구현한다. full 경로와 batch 평가 호환성을 유지한다. REFACTOR/자체REVIEW/필요한 전체 부품 회귀 후 커밋·공개CI를 확인한다.
- [ ] 별도v53 freeze/build/audit/실행source일치를 확인하고 기본 Level2·Level3를 각 최대1회 검증한다. 이것은 새 기본 모드 종료 경계 검증이며 충돌 해결 시도나 튜닝이 아니다. 실패 시 설정을 바꿔 재시도하지 않고 결과·종료·원인을 그대로 남긴다.
- [ ] 학생용 START_HERE, Level2 과거 시연 해설, 향후 과제, 최종 검증/인수 범위를 작성하고 기존 가이드·종합보고의 첫 안내를 새 목표에 연결한다. 원래 FAIL/freeze/3회중단은 보존한다.
- [ ] 증거와 로그는 필수 항목만 압축/hash 보존하고 대형 중복은 검증 후 정리한다. 최종 커밋·게시/공개CI 확인 후 사용자 검토 자료를 제시한다. main 병합이나 전체 연속 미션 성공 인수는 대신 처리하지 않는다.

공식패턴은 기존13.7의설치버전조사와 native 테스트를 재사용하며, 이번 변경은 기존 Sequence.remove_child와 Session snapshot 계약에만 의존한다. 기본 실습 검증을 이유로 새학습·WBC·실기·일반인식·제어튜닝을 추가하지 않는다.
