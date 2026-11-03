# 시작 준비 수정 증거

`CASE_INDEX.json`은 v8/v9 실제 실행의 독립 판정을 구분한다. 두 동결을 같은 소스로 간주하지 않는다. 원본 실행은 각 UUID의 무손실 압축본으로 제공하고 모델·가중치는 재배포하지 않는다.

`diagnosis/`는 진단·수정 과정의 원본이다. 의도적으로 실패시킨 RED와 경고를 지우지 않았다.

- `camera_startup_both_red.log`: 초기화 오류 성공 오인, 조기 종료의 시간 초과 오분류.
- `startup_profile_red.log`: 초기화 실패 시 단계 기록 파일 부재.
- `resource_cleanup_red.log`: traceback 보존 시 실제 named semaphore 잔류.
- `resource_cleanup_green.log`: 실패·자원·카메라 시험 5 PASS.
- `final_suite.log`: 중간 181 PASS와 ResourceTracker 경고 17건. 최종 결과가 아니다.
- `final_cleanup_suite.log`: 최종 182 PASS, pytest 경고 없음.
- `freeze_v9.json`, `final_freeze.json`, `final_residual.json`: 동결·자산·소유 프로세스 확인.

완결된 별도 단계 관측은 `diagnosis/observed3/`의 카메라 6회와 DDS 시험 12회다. 개발 중 `console.log`, `observed/`, `observed2/`에 기록된 pytest 경로·Node 타입·legacy 계측 오류는 진단 도구 오류이며 제품 실패 통계로 세지 않는다. `observed2/`의 특정 latest 카메라 사례에서 정상 capture·publish 네 건과 수신 0건을 확인했으나, 이 혼합 진단 전체를 정상 인수 cohort로 사용하지 않는다.

`preparation_probe_source.py`는 감사용 진단 도구 원본 사본이다. 실제 실행 위치는 `.superpowers/sdd/SECTION_13_6_REUSE_IMPLEMENTATION_PLAN_KO/preparation_probe.py`였고 당시 실행 명령·원본 절대 경로는 로그에 남아 있다. 이 사본은 설치·실습용 runtime 도구가 아니며 현재 위치에서 직접 실행하도록 제공한 것이 아니다.

과거 준비 시간 초과의 세부 원인을 소급 확정하지 않는다. 이번에 확인하고 수정한 오류 전달·자원 해제·DDS 시험 준비 경쟁의 범위는 `SECTION_13_6_REUSE_PREPARATION_FIX_KO.md`를 참조한다.
