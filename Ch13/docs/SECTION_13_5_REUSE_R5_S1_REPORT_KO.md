# R5 S1 — 별도 설치·사전 검사·최종 기준 동결

2026-11-03 한국 시각. R4 실제 접근은35857406에서 개발 PASS다. 최종 여섯 시나리오는 아직 실행 전이다.

- 새 설치 경로 `/home/jinho/ch13_reuse_r5_build`에서 navigation_reuse, reuse_wire, 기존 vision 세 패키지만 빌드했다. Ch05~12를 빌드하거나 기존 underlay를 수정하지 않았다. C++ Release를 명시했다.
- [신규85개 회귀](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/tests.log): PASS/30.381s.
- [설치 감사](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/install_audit.json): 실제 설치31개 항목과 원본94개 자산 hash PASS. ELF는 CMake RPATH 차이와 실제 .text/.rodata 일치를 구분했다.
- [기존 관련 순수 회귀](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/legacy_pure_regressions.log): 13.3 policy, 13.4 geometry/freshness/camera_info 50개 PASS/1.74s. 기존 실기/전체 엔진·13.3 live lifecycle 회귀로 확대하지 않는다.
- 실제 Nav2 패키지 버전과 추론 pip 목록, 잔여 검사 결과를 같은 사전 검사 디렉터리에 기록했다.

최초 사전 검사에서 제가 설치 이후 촬영 tracker 계측을 추가해 설치본이 뒤처졌고 byte 감사가 이를 거부했다. 최초 로그를 보존하고 다시 빌드·검사한 v2 결과를 채택했다. 이어 기존 live lifecycle의 generated interface와 system Python의 MuJoCo가 이 세 패키지 환경에 없어 수집 오류가 났다. 관련 순수 회귀를 별도 실행했고 전체 old lifecycle/카메라 물리 PASS로 표시하지 않았다. 기존13.4 원본 사용자 문서는 수정하지 않았다.

## 실행 전 동결

`section_13_5_reuse_acceptance_v1.json`에 source/script byte SHA, 원본94자산 SHA, 시나리오와 수치를 고정한다. source/script 변경 시 덮어 쓰지 않고 새 개정이 필요하다. 실행은 순차이고 각 시나리오는 새 UUID다. 실패도 자동 보고서로 보존하며 자동 재시도하지 않는다.

자유 공간, 우회, 비어 있는 목표를 장벽으로 분리한 도달 불가, 취소, 실제 촬영 접근, raw 손실을 각1회 수행한다. 도착0.10m/0.10rad, 정착edu_stop_v2, zero결정0.35wall초, 정착8wall/5sim초, camera/source300ms와 과거TF100ms를 유지한다. 처리 선택15wallHz와 촬영 상한15wallHz·scan10wallHz를 명시한다. 기존 motorcap과 native jointlimit의 soft tolerance0.02rad는 실제500Hz 전체 최대값도 별도 계측한다. raw 손실은 소유 PID와 부모를 확인해 pause/restore하고 입력 복귀 뒤에도 gateway FAULT 유지 여부를 확인한다. 촬영 worker와 별도 tracker PID의 소멸도 검사한다.

정확한 능동 분석 공수 합계는 계측하지 않았다. 실행별 sim/wall과 빌드/테스트 시간을 분리 보관하며 날짜 차이를 공수로 환산하지 않는다. 최종 결과는 후속 R5 보고서에 기록한다.
