# Ch13 controller 최소 파생 명세

코드 복사는 세 파일뿐이다. 원본 URL·커밋·SHA256은 UPSTREAM_SOURCES.json에 기록했다.

- ros2_controllers4.42.1, 커밋 aacd842600a09d556b983ac3d53a0983e9ebcbb1:
  JTC 구현 cpp와 선언 hpp. Apache-2.0 저작권 헤더와 LICENSE를 보존했다.
- realtime_tools3.13.0, 커밋459776c99f1f80606f7b9616496166ccaf207cf8:
  realtime_server_goal_handle.hpp. Willow Garage 저작권·BSD-3-Clause 원문을 보존했다.

JTC cpp/hpp의 namespace와 include guard, plugin class ID를 Ch13 전용으로 분리했다.
trajectory·파라미터·tolerance 구현은 복사하지 않고 고정 설치본의 공개 API/라이브러리를
재사용한다. 기존 joint_trajectory_controller 클래스·패키지·underlay를 덮어쓰지 않는다.

동작 변경은 파생 realtime goal wrapper의 runNonRealtime 한 경계다. RT 성공/중단이
대기 중인 사이 취소가 수락되면 원본은 CANCELING 상태에서 결과를 발행하지 않는다.
파생본은 수락된 취소를 우선하여 실제 CANCELED result를 한 번 전달하고 대기 flag를 정리한다.
상태 토픽·cancel ACK로 result를 합성하거나 소유권을 해제하지 않는다. 기존 궤적 계산,
관절·속도·가속도 제한, command/state 인터페이스, hold 정책은 바꾸지 않았다.

실제 C++ 서버/클라이언트 경쟁 회귀는 Ch13 신규 코드다. 원본 실패와 파생 성공을
completion evidence/rt-goal-repro에서 같은 fixture로 비교한다. 새 패키지 테스트는
성공/중단 대기와 취소가 겹치는 두 경우의 실제 terminal 결과를 검증한다.

configure-time source_manifest와 설치 라이브러리 해시를 별도로 감사한다.
이 파생본은 설치된 JTC4.42.1·realtime_tools3.13.0을 명시적으로 요구한다.
다른 버전의 ABI/동작 호환은 자동으로 가정하지 않는다.
