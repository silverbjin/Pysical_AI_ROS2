# R5 S2 — v1 실패 보완과 v2 소스 동결

v1의4PASS/2FAIL과 원본 UUID는 별도 보고서로 보존·게시했다. 수치 게이트를 변경하지 않고 출발 준비와 영상 전달을 보완했다.

## RED → GREEN

- 실제 DDS 준비 단계에서 속도0을 기대했지만 기존 경계가0.1을 출력한 RED를 확인했다. 실제 controller/smoother를 신선하게 받은 ACTIVE에서도 zero를 유지하고, gateway가 fresh zero에서 재무장된 뒤 explicit release를 받아야 속도를 통과시킨다. 전체 실행기는 이 순서를 기록한다. 경로가 준비 중 ABORTED라면 gateway 재무장/속도 해제를 하지 않는다.
- camera receipt 결합의 누락 RED2를 확인했다. 큰 RGB-D는 원본 native ROS 메시지로 직접 수신한다. C++는 실제 sample GID/최초 monotonic receipt/source timestamp와 SHA256만 보낸다. 미정 CDR padding을 피하려고 전체 header·픽셀·encoding·calibration·ROI를 명시한 little-endian canonical1을 양쪽에서 계산한다. 실제320×240 RGB/depth/info/meta 네 종류의 C++↔Python SHA 일치를 DDS로 확인했고, 손상 native bytes·중복 재수신이 결합/시각을 갱신하지 않는 검사를 통과했다.
- 인식은10Hz 기본/15Hz 선택을 유지한다. 카메라 생존 확인과 검출점 승인/최종 인계의 신선도는 계속 분리하며300ms/과거TF100ms를 유지한다. 원본 raw/상태/Nav2 CDR 경로는 바꾸지 않았다.

[최종88개 검사](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/tests_88_final.log) PASS/31.502s. [새 설치 감사](../evidence/section_13_5_reuse/r5_preflight_20261103_v2/install_audit_native.json)는 실제32개 설치 항목/원본94개 자산 hash PASS다. 기존 관련 순수 회귀50개는 변경이 없는 범위에서 재사용하며 새 플랫폼 물리 성공으로 전이하지 않는다. OpenSSL3.0.13 헤더/라이브러리는 이미 설치돼 있었고 시스템 설치·권한·드라이버·시계 설정을 바꾸지 않았다.

## 동결과 다음 실행

v2에는 소스·도구 hash와 같은 여섯 시나리오를 다시 고정한다. v1 JSON과 FAIL을 덮어 쓰지 않는다. 실측 도착·정착·age·cap·종료 기준은 v1과 동일하다. 실제 시나리오는 새 UUID에서 각1회 순차 수행하고 자동 재시도하지 않는다. 최종 결과는 R5 보고서가 기록한다.
