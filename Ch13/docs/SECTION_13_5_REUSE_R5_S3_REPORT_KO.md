# R5 S3 — 전체 명령 인계의 시각 역행 수정과 검증 누락 보완

v2 원본 결과는 [별도 보고서](SECTION_13_5_REUSE_R5_V2_REPORT_KO.md)로 보존한다. 영상 전달은 실제509개 관측·거부0·health 검증 age 최대150.02ms였으며 만료 문제가 재현되지 않았다. 이동 실패는 platform의 SOURCE_REORDER:safe였다.

## 재현한 원인과 수정

100ms 지연된 원본 zero를 실제 DDS로 넣자, gateway 재무장 시 safe header가2.12→2.04sim초로 돌아가는 RED를 재현했다. DISARMED에서 생성 zero의 stamp가 현재 clock을 따라 앞서고, ARMED에서 제어기 원본 stamp로 돌아갔기 때문이다. boundary 한 곳의 준비 상태만으로 해결할 수 없는 전체 경계 문제였다.

DISARMED zero는 원본 raw 시각과 마지막 발행 watermark를 따라가며 오래된 원본은 반복 시각으로 유지한다. nonzero 명령을 now로 바꾸지 않는다. 원본 stamp가 watermark에 도달하고 fresh zero가 확인될 때만 gateway를 재무장한다. 플랫폼은 그 후 재무장하고 마지막에 boundary를 explicit release한다. 누락/clock/owner fault와300ms 원본 계약은 유지한다.

[전체89개 검사](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/tests_89_safe_handoff.log) PASS/27.817s. [새 byte 감사](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/install_audit_v3.json) 실제32항목·원본94자산 PASS. 지연된 safe header가 역행하지 않는 actual DDS 회귀를 포함한다.

## 취소 증거 검증의 누락

v2 취소 사례는 정지·terminal·회수는 확인했지만 platform fault 때문에 원래 움직이지 않은 상태였다. 이전 checker가 이를 부분 PASS로 표시한 것은 검증 누락이다. 원본을 덮어 쓰지 않고 [별도 재분석](../evidence/section_13_5_reuse/f5c2285d-6972-456b-9deb-fa765f0b6156/v3_reanalysis_from_v2_cancel.json)에서 FAIL을 확인했다. 실제 engine 궤적의 움직임 증거는3.76mm에 불과했다.

최종 checker는 예상하지 않은 platform fault를 허용하지 않는다. 취소/손실 전에는 실제 engine 궤적에서 기존 정착 noise envelope0.03m를 넘는 이동을 요구한다. 이는 원래 요구한 실제 이동 증거의 누락을 보완하는 검사이며 운전·정지 허용오차를 넓히지 않는다. v3 JSON에 이 증거 기준을 명시하고 원본 v1/v2를 보존한다.

## 다음 실행

v3를 새 source/script SHA로 동결하고 여섯 시나리오를 각1회 새 UUID에서 실행한다. 최종 결과 전에는 완료/PASS로 표시하지 않는다. 기본 운전 cap·도착·정착·age·시계·회수 기준은 그대로다.
