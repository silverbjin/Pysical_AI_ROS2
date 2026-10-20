# 실제 엔진 인수 조건

실행 묶음 UUID: edfdbd00-7970-4073-8664-8c8902614b99.
코드 체크포인트: a7ab923f58d640e65db6e1f9276024db96f3e421.
브랜치: feat/ch13-section-13-4. 네이티브 실행, 서브에이전트 없음.

새5패키지 설치: `Ch13/ros2_ws/install13_4_snapshot_full_35954ef5`.
underlay: ROS Jazzy + 고정 mujoco_ros2_control c261f5552edf124d1000a23fb25b6c07cadeb807.
venv: `/home/jinho/ch13_vision_13_4_venv`. 설치 감사 원본을 이 묶음에 별도 보존한다.

RGB-D320×240, 카메라 목표15Hz, 추론10Hz/명시적15Hz, 촬영·receipt300ms,
TF100ms, 팔 명령 상한5Hz, 각도.04rad/속도.1rad/s를 유지한다.
LP_NUM_THREADS·driver·해상도·안전 기한 변경 없음. GPU/renderer는 실제 로그로 확인하며
환경 변수만으로 하드웨어 가속을 주장하지 않는다. 두 플러그인의 CMake build type과
공통 CXX flags는 모두 빈 기본값이다.

각 실행은 독립 output/run UUID를 사용한다. 종료와 잔여 PID를 확인한 뒤에만 다음
엔진을 시작한다. 안전 정지한 trial을 재활성화해 성공으로 이어 붙이지 않는다.
성능 시험 중 build/대량 pytest를 병행하지 않는다. 감독자가 소유하지 않은 PID를
종료하지 않으며 관리자 권한/ptrace 정책 변경을 하지 않는다.

기본 backend 전환은 MuJoCo 국소 인수·10Hz 독립3회·기존 회귀가 모두 통과한 뒤에만
판정한다. 실패/미실행과 과거의 성공은 분리한다. 전체13.4가 미달이면13.5는 보류다.

짧은 디렉터리명은 Windows 경로 길이 제한을 피하기 위한 것이다. 전체 실행 UUID와
원본 결과의 run_id/해시가 식별 기준이며 이름만으로 PASS를 판단하지 않는다.
