# Level 3 변경 없는 단일 검증 결과

작성일2026-11-12 KST. 사용자 지시에 따라 Level2 반복 튜닝을 중단하고 기존Level3를 한 번 검증했다. 구현·파라미터 변경이나 실패 후 재시도는 하지 않았다. **문 통과·fresh find는 PASS, PRE_GRASP 경로 검증은 FAIL이며 파지·운반·놓기는 미실행이다.**

## 실행 기준과 결과

- 명세/기준 검토: SECTION_13_8_STATUS_CRITERIA_LEVEL3_SWITCH_20261112_KO.md, commit659fe1e6. 공개CI43048295357/job130618117971/runner1000006066의모든step success.
- 실행 UUID: e475ece0-9f70-4dae-8de9-491ee92c95fc. source v51/400파일·외부94자산/SHA4cb73b008679472f8d792e29e97283c4a43d85a33eced36e9de1c34e4ecf56c7. 기존502 native시험/설치감사/실행source 일치를 재사용했다. 문서 변경 때문에 전체시험을 반복하지 않았다.
- Level3 기존NavFn+전진RPP,SE2=0,15Hz,overlap1,계측1. Scan은기존mj_ray다. Level2 전용DUBIN/batch/목표보간overlay가 적용된 실행이 아니다.
- trial48.844sim/178.990wall초, CPU48.995%/허용8core정규화, 최대roll/pitch .056271rad. 중단까지의값이며 완주시간·완주CPU·최종귀환오차가 아니다.
- world witness는door_passage/target_below_table/fresh_find 모두true다. Navigate/Find가 완료됐으며 gripper개방을실행한뒤 PRE_GRASP 계획으로 진행했다. 원고의 전체 연속미션 성공은false다.

## 최초 실패와 공식 구현 대조

두등가roll 후보 모두/plan_kinematic_path 응답error_code99999로거절됐다. planning_time은1.014583/1.019161초이며 scene_hash는동일6a0640802111e24adb0cf7638e261eec53557a57aed637ace9f4ec38ff8944bc다. 실행코드 planning.py는SUCCESS1인응답만candidate로반환하므로 pre-grasp 6D pose planning failed assertion으로종료됐다.

planner로그의첫후보에서는reuse_table_top↔reuse/link3,두번째후보에서는reuse_table_leg_0↔reuse/link7 충돌이기록됐고 ValidateSolution이INVALID_MOTION_PLAN을반환했다. 이는계획상태의충돌이며 실제팔이식탁과충돌했다는뜻이아니다. arm trajectory는실행되지않았다. 반환자료에trajectory가있거나긴duration이있어도계획SUCCESS/실행허가가아니다. 이번최초실패를120초action timeout이나수명만료로바꾸어설명하지않는다.

설치버전MoveIt2.12.4의[공식validate_path.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning/planning_response_adapter_plugins/src/validate_path.cpp)를확인했다. 파일명과클래스명이다르며클래스는ValidateSolution이다. isPathValid가충돌·실행가능성·제약충족을검사하고유효하지않으면INVALID_MOTION_PLAN으로거절하는패턴이다. 최초validate_solution.cpp URL은404였고공식tag의파일목록으로실제파일을찾았다. 이조회실패는로봇실행실패가아니다.

과거v28의endpoint계획실패와관련계열이지만현재table충돌쌍을과거base/link3 자기충돌과동일원인으로단정하지않는다. 저장endpoint IK성공이전체시간파라미터화경로의충돌없음을보증하지않는한계가다시확인됐다. 충돌검사를끄거나형상·허용치·정착위치를변경하는튜닝은하지않았다.

## 안전 종료와 보존

engine COMPLETED/normal_shutdown_requested=true/final_fault빈값. planner를engine보다먼저정지했으며자식12개정상회수,launch exit0,remaining_launch_pids[],최종소유잔여[]/공유lockfree다. 정상종료는미션성공과구분한다. 관측거절통계에expired1건이있으나이번terminal의직접원인은MoveIt계획거절이다.

정확한source400파일보존PASS/source archive SHA12a4332dbe6b558c8fb4d946082d8160ca2213567771415cb456820fbfc92952. raw.tar.gz17,070,426bytes/SHA29603e2e476eb71631686f7ce975c9fdbb71678122bf48fd0409295b00e142d6. raw_manifest/원래trial/계획응답/충돌로그/종료증거를보존했다. 소스·모델·실제파지결과를새로만들지않았다.

지속적인 디스크 관리 지시에 따라 종료된 v49/v50/v51 Level2와 이번 Level3의 대형 비추적 중복37파일331,527,303bytes를 정리했다. 삭제 전 archive 전체 SHA와 각 멤버/로컬 SHA·절대 경로를 검증했다. 압축 증거·판정·정확한 source는 유지한다. receipt는 retention_v49_v51_level3_20261112.json이다. raw_manifest의 원본 존재 정보는 생성 당시 기록이며 현재 대형 원본은 해당 archive 멤버로 복원한다.

## 현재 상태와 다음 경계

Level2 추가튜닝중단,Level3 baseline확인완료·정상완주미달. 원래정식v28은0/10으로유지하며이번1회를분모에섞지않는다. 새10회평가나Owner인수는진행하지않았다.

도서제공관점에서는기존구성의문통과·관측·충돌계획거절·안전종료를재현가능한결과로설명할수있다. 파지·귀환·놓기가검증완료된패키지라고제공할수는없다. 원고목표와추가개발witness를분리한기준검토는전환보고서에있다. 후속개발이필요하면현재저장실패의MoveIt계획경계만독립적으로검토해야하며,이번지시하에서는자동튜닝·반복engine실행을추가하지않는다.
