# 13.4 실험 브랜치·증거 보존 판정

2026-10-20. 최종 사용자 선택: **현재 실험 브랜치와 증거만 보존**.
이 인계는 구현 완료나 전체 인수 PASS가 아니다. EGL 재설계·추가 실측·13.5는
진행하지 않았다. 원본 결과 JSON과 실패 로그를 수정하지 않고 주석을 별도로 남긴다.

## 미해결 중요 결함: GLFW 메인 스레드 계약 (P1)

설치된 /usr/include/GLFW/glfw3.h의1798/2692/2721행은 각각 glfwInit,
glfwCreateWindow, glfwDestroyWindow를 메인 스레드에서만 호출하도록 규정한다.
반면 snapshot_camera_plugin.cpp의50행은 별도 std::thread를 시작하며,
update_loop(412행)의430/435/437행에서 이 API들을 호출한다.
확인 원문과 호출 위치는 [glfw-contract.log](glfw-contract.log)에 보존했다.

렌더 데이터·GL context를 worker 하나가 소유한다는 것과 GLFW API의 메인 스레드
계약 준수는 다르다. 실제 GL 시험과 기하·YOLO의 일부 성공으로 계약 위반을
무효화할 수 없다. 현재 snapshot backend는 실험 코드이며 사용을 권장하지 않는다.
기본 upstream 유지도 외부 카메라 구현의 안전성 인증을 의미하지 않는다.
MUJOCO_GL=egl 환경변수만으로 해당 C++ GLFW 경로가 EGL로 바뀌지 않는다.
현재 실측 렌더러는 GLFW/llvmpipe다. worker 전용 EGL 경로는 제안일 뿐 구현되지 않았다.
이 결함이 모든 시간 초과·종료 실패의 단일 원인이라는 인과 주장도 하지 않는다.

## 보존된 측정과 한계

- 네이티브 소스 checkpoint: 6828b82fd13c97dba3fc935325a741e583a830aa.
  주실험23회(10PASS/13FAIL), 별도 clean7회(1PASS/6FAIL).
- clean10Hz3회와15Hz3회 추적 모두 FAIL. 300ms·TF100ms·팔5Hz 기준 불변.
  MuJoCo joint-loss의 terminal 응답, Gazebo 추적/image-loss/정상 종료도 미달이 남는다.
- 정적/지연 기하와 실제 컵 YOLO의 일부 관측은 유효한 실행 기록이나,
  위 GLFW 제약을 고려한 지원 가능한 backend 인수는 입증하지 못한다.
- 후속 검증기 경계 수정 checkpoint: d6f33bfdcd63051500ee09cc419727d171994f60.
  기존 최종 로그는 소스285 PASS, 패키지123건 오류0/실패0/skip0,
  설치 감사 PASS를 기록한다. 본 보존 단계에서 테스트나 엔진을 다시 실행하지 않았다.
- evaluation2/summary.json(run4ec9b314-2421-489c-a9bb-13a2efd49da4)은
  완료된 실행의 사후 집계이며 새 시뮬레이션이 아니다. 전체 FAIL이다.
  최초 evaluation의 빈 로그 등록 오류도 삭제하지 않았다.
- 물리 파지·PPO 안정성·MoveIt·Nav2·실로봇·GUI는 미검증이다.
  TSAN 최신 실행도 시작 시 memory mapping 오류로 미검증이다.

## 인계와 무결성

작성자 자체 리뷰만 수행했다. 독립 리뷰는 사용자 네이티브/서브에이전트 금지
요청에 따라 수행하지 않았으며, 리뷰가 clean하다고 선언하지 않는다.
main 병합·13.5 재개·실로봇 배포의 근거로 사용하면 안 된다.
Ch05~Ch12와 외부 원본은 수정하지 않았다. 관리자 권한·시스템 정책 변경은 없었다.

작업 판단과 비용은 보존한 [EXECUTION_LEDGER.md](EXECUTION_LEDGER.md)를 따른다.
archive-audit.py는 보존 파일의 바이트/SHA 및 등록 artifact 참조를 재검사한다.
archive-index.json의 integrity PASS는 제품 인수 PASS가 아니며 native_acceptance는 FAIL이다.
기록된 PID/PGID는 역사적 식별자이므로 현재 프로세스를 종료하는 데 재사용하지 않는다.
기존 미정리 작업 공간도 리뷰가 미완료이므로 삭제하지 않았다.
