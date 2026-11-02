# SECTION 8.3 코드 리뷰 — Gymnasium 인터페이스

- 기준: 2026-10-20 KST, main `38fb4647aeff2d3ab951404d78e1812e598f2308`
- 참조: 원고 8.3.1~8.3.5, `Ch08/ros2_ws/my_robot_env.py`, `test_env.py`, `src/my_robot_description/assets/simple_arm_3dof.xml`
- 판정: **정적 조건부 적합, 제어 정규화 및 시드 재현성 결함**. 소스 리뷰만 수행; Python 의존성이 없는 작업 환경으로 런타임 PASS를 주장하지 않는다.

## 현재 계약
`MuJoCoArmEnv`: `action_space=Box([-1,1], shape=(3,))`; 관측은 `qpos[:3]`, `qvel[:3]`, `target_pos(3)`, `target-ee(3)`를 연결한 `float32[12]`; `reset`은 `(obs,info)`, `step`은 `(obs,reward,terminated,truncated,info)`를 반환한다. XML의 `link_ee`는 실제 이름과 일치한다.

## 발견 사항
| ID | 등급 | 근거·영향 | 개선 제안 |
|---|---|---|---|
| 8.3-R1 | HIGH | `my_robot_env.step`은 `self.data.ctrl[:] = action * 50.0`; XML motor는 이미 `gear="50","50","30"`, `ctrlrange="-1 1"`을 지정한다. 제어 입력 계약이 중복/클램프 의존 상태다. | `action=np.asarray(...)` 검증·클리핑 후 `ctrl=action`, 힘 환산은 gear 기반 확인 |
| 8.3-R2 | MEDIUM | `reset(seed)`에서 `super().reset(seed=seed)` 호출 뒤 전역 `np.random.uniform` 사용 → 동일 seed의 목표 재현 보장 안 됨. | `self.np_random.uniform`으로 변경, 시드 회귀 추가 |
| 8.3-R3 | MEDIUM | `render_modes`에 `rgb_array`를 광고하지만 `render()`는 human만 동작하고 RGB 이미지를 반환하지 않는다. | `rgb_array` 렌더러 구현하거나 지원 목록에서 제외 |
| 8.3-R4 | MEDIUM | `truncated=False` 고정, 무제한 에피소드; `test_env.py`는 외부 루프 1000번으로만 종료한다. | `TimeLimit` wrapper 또는 env 최대 단계로 잘라 학습/평가에서 사용 |
| 8.3-R5 | MEDIUM | 모델 경로를 CWD 상대 경로 `src/my_robot_description/assets/...`로 지정. | `Path(__file__).resolve().parent` 기반 경로 |
| 8.3-R6 | LOW | `step(action)`의 action shape, finite 값 확인이 없다. | `action_space.contains` / 값 범위 유효성 테스트와 비정상 입력 처리 |
| 8.3-R7 | LOW | 원고 8.3의 9차원 설명과 실제 소스의 12차원이 다르다. | 설명을 '9차원 기본형/12차원 개선형'으로 나눠 표기 |

## 권장 테스트·기대치
1. headless `MuJoCoArmEnv(render_mode=None)` 생성 후 `obs.shape==(12,)`, `action_space.shape==(3,)`, `np.isfinite(obs).all()`.
2. `env.step(np.zeros(3,dtype=np.float32))`에서 5개 반환 타입과 거리값 유한성 검증.
3. 똑같은 seed로 두 번 `reset`한 목표 슬라이스 `obs[6:9]` 비교. **현재 소스는 일치 실패 가능성이 높은 결함**, 랜덤 우연 가능성을 고려해 다수 seed 확인.
4. `stable_baselines3.common.env_checker.check_env`를 호출해 API 위반 발견 여부 기록. 이 함수가 문제 없이 끝나도 성능/보상의 올바름까지 보장하지 않는다.
5. `render_mode="human"`의 `test_env.py`는 WSLg 세션에서만 실행·기록.

**수정 우선순위:** 액추에이터 정규화 → 시드 → TimeLimit → RGB → 경로. 이번 브랜치는 문서만 작성하며 코드 수정·실행 성공 증거는 포함하지 않는다.

[실습 가이드](LAB_8_3_GUIDE_KO.md)
