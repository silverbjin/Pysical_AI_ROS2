# 13.6 M3/M4 개발 중간 기록

2026-11-03 KST. M1·M2 완료 이후의 구현 checkpoint이며 **M3 전체 인수·물리 파지 완료 보고서가 아니다.**

통합 MuJoCo 모델에서 로컬 URDF/SRDF를 생성하고 20개 무작위 자세의 FK를 1e-8 수준으로 대조했다. 실제 MoveIt RobotModel의 TCP도 비교했다. planning group·실제 floating base·gripper mimic·물리 collision proxy가 포함된다. 모델/mesh/가중치를 새로 배포하지 않는다.

Python 래퍼와 단일 MoveGroup 장면을 연결했다. OMPL/TRAC-IK 자세 계획, 도달 불가·충돌 거절, 전체 Cartesian 경로, 실제 팔 execution·취소가 구현됐다. 기본 MoveGroup의 종료 문제를 확인하고 공식 capability의 수명만 소유하는 작은 C++ 호스트로 회수했다. API·PD 보상·수명 변경은 [별도 설계 기록](SECTION_13_6_REUSE_ENGINEERING_DECISIONS_KO.md)에 명시했다.

## 보존한 결과

| UUID | 확인 결과 | 인수 해석 |
|---|---|---|
| `4a1333df-e0a3-492c-9e42-4d36946bb110` | 초기 궤적 frame/끝 derivative 거절·기본 MoveGroup 종료 실패 | FAIL 보존 |
| `2ece9bb8-1960-44de-b92b-31325ae5dc18` | 계획 원본 저장·기본 MoveGroup 종료 실패 | FAIL 보존 |
| `8ae14816-b5cf-4c39-9eaa-e6101defec25` | 관절 계획 실제 도달 3.63mm, 긴 자세 admission에서 만료 | 전체 FAIL |
| `63bcc5a6-e00f-4d3b-96f2-cf0a9c553d9b` | 동기 admission을 분리했으나 0.813wall초 engine loop gap·관측 만료 | 전체 FAIL |
| `5e6bcd8d-8751-4d65-9e0a-7c557bf328ce` | 관절/pose/Cartesian 실제 오차 3.64/2.70/2.94mm, MoveGroup 사용자 취소 응답 실패 | 전체 FAIL |
| `416b6c0a-f1a3-44a6-a712-c2ae506a5154` | MoveGroup 취소 대기 연장으로도 사용자 취소가 전달되지 않음 | 전체 FAIL, 실행 경로 재설계 |
| `660ec362-e61c-4a78-b0e1-86bbb38a31fc` | native trajectory 경로로 실제 세 도달 3.52/3.85/3.05mm·취소 ACK 7.45ms·실제 CANCELED | summary PASS였으나 gateway fault를 놓쳤으므로 전체 PASS 불인정 |
| `7765fa2e-6340-4b27-bdb4-56a12853d09d`, `5f9f36a0-732c-4ef6-bc29-c3a1ba42721c` | 팔 이전 접근 중 VISION_EXPIRED | 기존 간헐 지연으로 별도 FAIL 보존 |
| `7392cbb4-8b44-4fe9-a0fb-2e8bb9eb5df3` | 팔 이전 startup FUTURE_SOURCE:base | FAIL 보존 |

`660ec362` 이후 gateway의 13.5 hold 가정(팔±0.1rad)을 opt-in 실제 한계 검사로 분리하고, native gateway fault·수신 만료를 엔진 lease에 전달했다. 후속 mission/독립 verifier도 gateway fault를 검사한다. 이 수정 후 전체 M3 PASS는 아직 이 문서에서 선언하지 않는다.

계획기 수명 단독 시험의 초기 segfault/GDB/weak pin 실패도 각각 `d4d192ca`, `63b5270a`, `b479910f`에 보존했다. 코드 수명을 유지한 `2abf3f9a-cb3b-4d40-b83d-8f56233c46d1`은 0.367초 정상 종료와 PLANNER_JOINED를 확인했다. debugger의 exit 0을 native 성공으로 대체하지 않았다.

## 물리 파지 진행

동적 원통·RGB-D 표면 fit·좁은 접촉 허용·독립 물리 인수 도구를 구현했다. 반경2cm/높이8cm/20g/마찰0.8·원본0.5N cap은 [사전 계약](../dependencies/section_13_6_pick_contract_v1.json)에 고정했다. 대상 freejoint는 평가 전용 파일에만 기록한다.

첫 `c2708b43-38a1-4e62-974d-710992d67c2f`는 788점 pre-grasp 계획 뒤 관측 만료로 실제 안전 정지했다. 경로점을 보존한 일괄 수치 검증으로 replay 검증10.6ms·시간 조정36.5ms를 확인했다. 두 번째 `0dc72e43-46b1-4f7e-a8d0-26b7833cb5a4`는 두 원통 roll 대칭 중53.478sim초 경로를 선택했지만 이동 시작 약20wall초 뒤 MISSION_EXPIRED로 정지했다. 접촉·들기에 도달하지 않았으며 물리 파지 성공은 없다. 후속 실행에는 mission 발행·원본 수신·엔진 처리 시각을 분리 기록한다. TTL 완화나 물리 수치 탐색으로 우회하지 않는다.

새 부품 suite는 관절 경계·실제 모델·원통 fit·freejoint 보존·독립 인수 등을 포함해56개 PASS를 확인했다. 실제 엔진은 순차 실행했고 설치 감사/회수 검사를 사례별로 남긴다. 최종 freeze·전수 인수·13.5 회귀·가이드 검증·게시 완료는 아직 남아 있다.
