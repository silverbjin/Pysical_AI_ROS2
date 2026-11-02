# R4 S2: 실제 영상 경로와 시간축 보완

R4 진행 보고다. 아직 비전 접근 성공과 R5 완료를 주장하지 않는다. 원본 촬영·최초 receipt와300ms 만료 기준은 유지했다.

## 실제 실패와 진단

| 실행 | 결과 | 핵심 |
|---|---|---|
| [87a23223](../evidence/section_13_5_reuse/87a23223-e51f-4aab-b7a4-42301c69ec66/navigation_summary.json) | FAIL; clean 11/11 | inline renderer; VISION_EXPIRED |
| [8f15fd06](../evidence/section_13_5_reuse/8f15fd06-1441-45be-bfad-f7fdbb9e109f/navigation_summary.json) | FAIL; clean 11/11 | admission source age; VISION_EXPIRED |
| [4c9d68cd](../evidence/section_13_5_reuse/4c9d68cd-5437-4ec4-88dc-dd0d33c6524d/navigation_summary.json) | FAIL; clean 11/11 | continuous capture lease; VISION_EXPIRED |
| [6bd98251](../evidence/section_13_5_reuse/6bd98251-e812-48aa-bf22-0cb9bf0784f4/navigation_summary.json) | FAIL; clean 11/11 | renderer process-local threads; VISION_EXPIRED |
| [a4ce9164](../evidence/section_13_5_reuse/a4ce9164-3178-4187-a006-4761cb984b83/navigation_summary.json) | FAIL; clean 11/11 | collision-proxy camera; VISION_EXPIRED |
| [9cf8e81f](../evidence/section_13_5_reuse/9cf8e81f-5504-427b-89b0-b776bc361b57/navigation_summary.json) | FAIL; clean 11/11 | bounded ORT; VISION_EXPIRED |
| [a21acb4f](../evidence/section_13_5_reuse/a21acb4f-e4fa-48a4-9c93-23325f465341/navigation_summary.json) | FAIL; clean 11/11 | wall camera; NAV_INPUT_TIMEOUT |

## 적용한 구조 보완

- renderer를 단일 최신 슬롯·별도 worker로 분리하고 종료 join을 검사했다. 실제 qpos 복사·source capture/TF를 보존한다. RGB/depth 원본을 보관해 관측점 재계산 검사를 추가했다.
- 서비스 탐색은 계획 전에 끝내고, 계획 후 새 촬영이 경계에 도달한 뒤 출발한다.
- 고해상도 장식 robot mesh 대신 원본 collision 형상으로 촬영하는 교육용 화면을 명시했다. 부품24장 시험 최대19.05ms; 실제 접근 성공을 대체하지 않는다.
- upstream 기본 ORT 자동 스레드를 프로세스 내부1/1·순차·no-spin으로 제한했다. 고정 actor 출력 원본과1e-6 이내 일치 시험을 통과했다. 정책·학습·관측/action은 바꾸지 않는다.
- 시뮬레이터가 느릴 때15simHz/10simHz 센서가 wall300ms 계약을 어겼다. 촬영15wallHz·scan10wallHz로 요청하고 각 실제 상태의 sim header와 최초 capture wall을 유지한다. scan_time도 실제 sim 측정 간격이다.
- 단조시계 pacing은 원본 loop의 절대시계 변화에 따른 긴 sleep을 막는다. 시스템 시계를 변경하지 않는다.

## 검증과 다음 단계

[82개 회귀 로그](../evidence/section_13_5_reuse/r4_preflight/tests_82_wallsensors.log)를 확인한 뒤 이 고정 소스에서 실제 접근을 다시 시험한다. 이전 FAIL은 보존한다. 교육용 정착 gate SHA는 변경하지 않는다.

기록 정정: camera_component의 요약은 LP_NUM_THREADS=2 비교 호출에서 갱신돼 최대56.01ms이며, 예전58.24ms의 독립 원본 로그로 사용하지 않는다. 이후 component 경로를 인자로 받게 하여 camera_proxy 등 별도 디렉터리를 사용했다.
