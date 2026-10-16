# 12.1절 구현 리뷰 기록

검토일: 2026-10-17 KST. 기준: main `58fb5a0`, 작업 브랜치 `feat/ch12-section-12-1`.

별도 검토 에이전트가 승인된 설계, 환경·MJCF·데모·패키징·테스트·실습 가이드를 읽고 검토했다. 이후 검토자도 Ubuntu-24.04에서 실제 MuJoCo 테스트와 반복 물리 실험을 독립적으로 실행했다. Gazebo 통합 재검증은 구현자가 리뷰 지적을 반영한 뒤 수행했다.

## 확인 및 수정

- 관절 순서·토크 한계·MJCF 관절 영점 회전과 Ch11 주요 제원, MuJoCo free-joint 속도 좌표계를 확인했다.
- reset, seed, 낙상/시간 제한, 행동 입력 검증, 렌더러 자원 정리, wheel에 모델 포함 여부를 검토했다.
- **이전 결과 잔류:** Gazebo 조기 실패 때 과거 PASS 파일이 남을 수 있었다. 시작 시 이전 결과와 launch 로그를 제거하고, 관측 결과와 최종 결과를 분리했다. EXIT 처리에서 현재 실행의 최종 JSON을 기록한다. 잘못된 ROS_DOMAIN_ID로 조기 실패시켜 FAIL 기록을 확인했다.
- **종료 대기:** 처음에는 launch 부모의 생존 여부만 확인하고 TERM 이후 무기한 기다릴 수 있었다. 자신의 프로세스 그룹을 기준으로 제한 시간 동안 기다린 뒤 TERM/KILL을 적용하도록 했다. 강제 정리가 필요하면 정상 종료로 인정하지 않는다.
- 초기 RGB 테스트에서 함수 내부의 `import mujoco.viewer`가 `mujoco`를 지역 변수로 만들어 UnboundLocalError를 일으켰다. `from mujoco import viewer`로 수정한 뒤 실제 EGL 렌더링 테스트로 확인했다.
- 첫 Gazebo 관측은 통과했지만 프로세스 그룹 전체에 보낸 SIGINT와 launch의 신호 전파가 겹칠 수 있었고 종료 중 ROS 예외가 기록됐다. launch 부모에게 먼저 SIGINT를 보내는 방식으로 바꾸고 실제 재실행으로 확인한다. 최종 결과는 수정 보고서와 `evidence/gazebo/result.json`을 기준으로 판단한다.
- 추가 실행에서 ROS 노드는 정상 종료했으나 Gazebo CLI 래퍼가 SIGINT 뒤 남았다. 공식 `/server_control` 서비스에 `stop: true`를 보내면 GUI·서버·CLI가 정상 종료하는 것을 독립 실행으로 확인했다. 최종 스크립트는 이 종료 요청의 Boolean 응답까지 확인하고 ROS launch를 종료한다. 이 요청은 실험 고유의 GZ_PARTITION에만 전달한다.
- 종료 서비스의 `timeout`에도 `--kill-after=2s`가 필요하다는 추가 지적을 반영했다. 서비스 응답 직후에는 CLI가 아직 종료 중일 수 있으므로, 정상 종료 로그를 최대 10초 기다린 뒤 ROS 종료 신호를 보낸다.

## 독립 실행 결과

검토자가 `CH12_TEST_RENDER=1 MUJOCO_GL=egl python -m pytest Ch12 -q`를 실행하여 23개 통과, skip 0개를 확인했다. 4개의 무한 범위 Box 경고는 구현자 실행과 같았다. 이어 `verify_mujoco.py`로 실제 12 × 1,000 제어 스텝을 재실행하여 PASS를 확인했다. 두 관측 모드 모두 stand는 seed 0/42/123에서 낙상 0회, random은 각각 낙상 27/24/23회로 구현자 결과와 일치했다. 증거는 `evidence/reviewer_tests.log`, `reviewer_mujoco.json`, `reviewer_mujoco.log`에 보관했다.

리뷰 후 환경·모델·데모·패키지·가이드에서 추가 조치가 필요한 지적은 없었다. 무한 범위 관측 경고, 모델 단순화 및 검증 범위는 실습 가이드와 최종 보고서에 명시한다.

최종 Gazebo 통합 재실행은 관측 PASS, 종료 승인 true, 강제 정리 false로 종료 코드 0을 반환했다. Gazebo·ROS 프로세스가 정상 종료했으며 잔여 실행 프로세스는 없었다. 다만 parameter_bridge가 종료 중 `Failed to delete datawriter` 진단 1건을 출력했다. 이 미해결 DDS 진단은 최종 보고서에 명시하며, PASS를 로그에 어떤 진단도 없다는 뜻으로 해석하지 않는다.
