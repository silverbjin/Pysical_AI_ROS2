# G04 다음 개발 프리뷰 (미실행)
14.5 코드 14-9~12: 기존 G03 detector와 latest-slot/epoch/freshness/TF 계약 위에서만 확장. G03 actual CPU L0/L1/L2 scoped evidence 유지.
| 단위 | 계획 | 검수 |
|---|---|---|
| T09 | parameter 선언, 타입/range/기동 전 검증 | 잘못된 값 거부, 중복 선언 없음 |
| T10 | atomic parameter callback, per-frame immutable snapshot | 정상 변경 반영, 잘못된 묶음 전체 거부, 동시 처리 일관성 |
| T11 | 모델 hot swap n→s, 후보 hash/class/shape/backend 확인 및 warmup, request/generation 식별 | 실제 추론 유지, 성공 전 기존 active 보존, 실패 rollback, 중복/busy 처리, stale 결과 방지 |
| T12 | 설치된 launch/YAML/CLI overrides | actual process launch, precedence, ROS replay 및 필요한 Gazebo 통합만 검수 |
GPU/WSL2 L3/release 별도. 기존 G01 절대 의미 검수 실패, legacy sparse-checkout, 자산별 배포권 HOLD. G03 고정 검증 장면/임계값을 변경해 성공시키지 않는다. G03 workflow 현재 final_faults 전용; 영향 분석으로 실제 필요한 phase만 명시 실행. G05 60초 종단 성능은 별도. main 승인 전 병합 금지. G04 NOT_STARTED.
