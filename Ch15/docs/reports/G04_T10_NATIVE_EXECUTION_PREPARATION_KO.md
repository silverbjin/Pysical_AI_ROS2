# G04 T10 — Native Level 2 실행 검수 착수 기록
2026-11-27 KST. 기존 T10 자산 해결 (45911815970, 94/94, 407 source freeze) 재사용. 기준 main 1931cac92585fc155357880b584c72c76d67257c, feature parent 32bef4e4878d7a7201879c5ac7a908bafff4f297, Draft PR #208.
## 목적 및 변경 범위
- 기존 Ch13 원본 build/env/audit/freeze/stage/runner/assessor를 그대로 호출. Ch01~14 변경 없음. T11, G03 재실행 없음.
- 독립 Ubuntu 24.04/Jazzy CPU Docker 이미지(기존 검수 digest), 원본 13.5 pip freeze 및 공식 BT deb SHA256 사용. apt 실제 버전 및 pip freeze 기록. 원본 BT deb 또는 pip lock 확보 실패 시 환경 차단으로 판정, 버전 임의 변경 금지.
- 새 CI 작업 공간의 별도 build/venv, 원본 94개 asset 실제 materialization 및 공유 lock. EGL 실제 renderer smoke. Native basic level2_obstacles 한 번, 기록 ON. 원본 10 assessor, 종료/잔여/lock, bag metadata 및 payload SHA256 확인.
- 증거는 항상 수집하되 외부 원본 자산 및 모델/가중치, 이미지, bag payload를 공개 artifact에 포함하지 않음. 공개 artifact에는 진단 로그/결과/metadata/원본 bag 파일 해시만 포함. 따라서 bag binary의 제3자 재분석은 이번 공개 artifact만으로 불가하며 G05 MCAP 수집과 별도.
## 현재 상태
코드 및 CI 진입점 준비; 이 보고서는 실행 결과가 아니다. CI 실제 run/job 및 artifact를 확인한 후 PASS/FAIL/BLOCKED를 별도 기록한다. 현재 G04 PARTIAL_PASS_T11 / T10 NATIVE_L2_NOT_RUN. Owner L3, Profile C, physical F01 및 publication/main merge HOLD 유지.
