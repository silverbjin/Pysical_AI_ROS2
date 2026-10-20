# 강제 종료 후 복구 및 추가 원인

2026-10-19 재개 시 HEAD는 `a7ab923f58d640e65db6e1f9276024db96f3e421`,
브랜치는 `feat/ch13-section-13-4`였다. 저장된 미커밋 코드는 두 신규 회귀 테스트뿐이었다.
이전 native matrix는 강제 종료 이전 이미 의도적으로 STOPPED였으며 잔여 PID 기록이 비어 있다.
일반 사용자 WSL(uid1000)에서 재개 시 엔진/pytest 잔여 프로세스가 없음을 확인했다.
중단된 RED 로그의 `FFF`는 최종 시험 결과로 쓰지 않았다.

## 관찰 → 원인 → 최소 수정

`../cam-edfdbd00/md/system.log`는 새 snapshot 클래스 초기화 후 기존 CameraPlugin의
자동 등록, overview/eye_in_hand의 5Hz streaming을 모두 기록한다. 네 주요 센서 토픽은
중복되지 않아 기존 소유권 검사를 통과했지만, 같은 물리 카메라를 다른 토픽으로 또 렌더링했다.
따라서 이전 static/cup PASS만으로 새 backend의 최종 성능을 인정하지 않는다.

고정 외부 소스 `mujoco_system_interface.cpp`의 `load_legacy_cameras()`는 원본 class ID가
명시됐는지 판별한다. 별도 Ch13 class ID는 원본과 달라 이 fallback이 실행됐다.
이 경로는 하드웨어 `auto_register_cameras`를 기본 true로 읽으며 false이면 등록하지 않는다.
외부 원본을 수정하거나 class ID를 원본으로 위장할 필요가 없다.

Ch13 Xacro에 선택 인자를 추가하고, MuJoCo launch에서 snapshot + vision=true일 때만
false를 전달한다. upstream/vision=false는 기존 true 기본을 보존한다. 관절 20개·TF·제어기·
카메라 정책/해상도·안전 기한을 변경하지 않는다. 소유권 검사에는 자동 토픽 여섯 개의
발행자 부재를 추가해 같은 결함이 다른 토픽에 숨지 못하게 한다.

## 테스트 우선 기록

- 전원 종료 후 신규 RED 재실행: 10 failed /30 deselected /14.38s.
  네 launch 조합에서 하드웨어 파라미터가 누락됐고 여섯 hidden topic을 잘못 허용했다.
- 최소 수정 후 launch/runner 전체: 40 passed /84.23s.
- 다섯 패키지 빌드: 5 packages finished /1min27s.
- 전체 소스: 276 passed /130.76s, `pytest.xml`과 `auto-camera-suite.log`.
- 다섯 패키지 test: 5 packages finished /1min23s, 설치 감사 `installed.json` PASS.
  최초 result 집계155에는 예전 XML 보관 사본32건이 포함돼 있었다. 사본만 절대 경계를
  확인한 뒤 ignored 계획 폴더로 옮겼으며 원본 결과와 기존 evidence는 보존했다.
  현재 결과의 재집계는 `auto-camera-result-current.log`를 사용한다.
- 수정 후 native 인수는 별도 실행 결과를 확인한 뒤 기록한다.

새 원본 로그는 이 디렉터리에 보존한다. 이전 evidence는 덮어쓰지 않는다.
이는 중복 렌더링 원인의 수정이며 모든 지연·추적 실패의 원인까지 증명한 것은 아니다.
