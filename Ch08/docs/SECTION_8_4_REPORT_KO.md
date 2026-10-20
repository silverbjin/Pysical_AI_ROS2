# SECTION 8.4 코드 리뷰 — ReachEnv 환경 설계

**기준:** 2026-10-20 / main `38fb4647aeff2d3ab951404d78e1812e598f2308`; 첨부 원고 8.4.1~8.4.5 및 `Ch08/ros2_ws/rl_env.py`, `test_reach_env.py`, `src/my_robot_description/assets/simple_arm_3dof.xml`, `simple_arm_6dof.xml`.

**판정: 원고와 모델 계약 불일치(HIGH).** 소스 직접 열람에 근거한 정적 진단이며, MuJoCo 물리 컴파일·뷰어·학습은 실행하지 못했다. 이 브랜치는 문서 추가만 수행한다.

## 실제 구현 계약
`ReachEnv`는 원고와 달리 `simple_arm_6dof.xml`을 로드한다. 현재 XML은 관절/액추에이터 6개, 모캡 목표 바디 `target`, EE 바디 `link_ee`와 site `ee_site`를 포함한다. `action_space`는 `shape=(model.nu,)` = 6. `_get_obs()`는 `qpos(nq=6)+qvel(nv=6)+ee_site(3)+mocap_pos(3)` = **18차원**을 반환한다. 원고의 [qpos(3),qvel(3),target(3),상대벡터(3)] = 12와 다르다. XML의 `timestep=0.002`, `step`당 물리 5회이므로 제어 스텝은 **0.010초=100Hz**다.

## 문제 목록
| ID | 심각도 | 파일·원인 | 영향/조치 |
|---|---|---|---|
| 8.4-R1 | HIGH | `rl_env.py`는 6DOF, 원고·주석·`test_reach_env.py`는 3DOF/12D, 목표 좌표를 `obs[6:9]`로 출력 | 현 관측에서는 해당 인덱스가 관절 속도, **목표는 `obs[15:18]`**. 3DOF/6DOF를 별도 클래스로 분리하거나 원고 개정 |
| 8.4-R2 | HIGH | XML timestep=0.002×5, `test_reach_env.py`가 0.05초(20Hz) 물리 제어 주기라 주석 | 실제 100Hz, `time.sleep(.05)`는 단지 시연용 표시 지연. 측정 기준 교정 |
| 8.4-R3 | MEDIUM | `reset`에 `mj_resetData` 없음, `qpos/qvel`만 수동 덮어쓰기 | 이전 episode의 ctrl·기타 시뮬레이션 상태 초기화 여부 검증 필요; `mj_resetData` 및 명시적 상태 재설정 권장 |
| 8.4-R4 | MEDIUM | `reset` 중 존재하지 않는 `target_joint` ID를 얻어 `self.target_jnt_id=-1`로 저장하지만 이후 사용하지 않음 | 현재 코드의 직접 충돌은 아니나 무효 ID 삭제/검증 |
| 8.4-R5 | HIGH | `truncated=False` 고정 | PPO rollout 중 성공 못하면 에피소드가 무한히 이어질 수 있어 Monitor 지표가 비거나 편향. 최대 단계 적용 |
| 8.4-R6 | MEDIUM | 6DOF XML의 다수 링크 충돌을 `contype=conaffinity=0`으로 해제 | 실제 물리 접촉·자기충돌 제약 검증에 부적절할 수 있음. 교육용 단순화 명시 |
| 8.4-R7 | MEDIUM | `info`에 reward 성분과 `is_success`는 있지만 `distance` 키 없음 | `evaluate_robot.py`의 거리 기반 정착 오차 계산 불가. 거리 키 추가 |
| 8.4-R8 | LOW | `target_jnt_id`와 주석·사용하지 않는 구 버전 블록 대량 잔존 | 새 6DOF 구현과 3DOF 원고 구분 위해 정리 |

## 권장 동적 검사
`mujoco.MjModel.from_xml_path` 로드, `model.nq/nv/nu`, `ee_site`, `body_mocapid[target]` 검사 → `reset` 시 목표 위치 갱신 → 100회 랜덤 `step`에서 관측 18, 유한 보상, 네이티브 bool 종료 조건 검사 → episode 타임아웃 적용·정착 오차 측정. 본 요청에서는 동적 실행 증거를 확보하지 못하므로 모두 **미검증**으로 둔다.

**권장 교육 설계:** 8.3의 3DOF 개념 환경과 8.4의 6DOF 확장 환경을 명확히 분리하거나, 코드 구현을 원고의 3DOF 계약으로 환원한다. 전자/후자 선택 전 모델/정책 파일을 혼합하지 않는다.

[실습 가이드](LAB_8_4_GUIDE_KO.md)
