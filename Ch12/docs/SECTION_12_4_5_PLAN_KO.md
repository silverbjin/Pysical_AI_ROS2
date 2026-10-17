# 12.4·12.5절 구현 계획

사용자가 제공한 초안과 고도화 허용 범위를 적용한다. 기존 12.1~12.3 API를 유지한다.

- [x] `ppo.py`, `train_ppo.py`, `play.py`: 선택 의존성 SB3, CPU 기본, Tanh 256×256 actor/critic, Dummy/Subproc 선택. 평가 간격은 총 전이 수를 환경 수로 나눈다. 별도 Monitor 평가 환경, TensorBoard, best/final/checkpoint, 과제·환경·학습 설정 manifest를 저장한다. 정규화 wrapper는 사용하지 않아 별도 통계 파일 누락을 피한다.
- [x] PPO 테스트: 실제 작은 rollout과 gradient update, 유한 파라미터·변화 검증, best/final 저장 후 로드·추론, TensorBoard 이벤트와 평가 파일, subproc 실행 확인. smoke 실행을 보행 학습 성공으로 해석하지 않는다.
- [x] `goal_env.py`: 독립 과제. 관측 48 = 고유감각 45 + 거리/sin(헤딩)/cos(헤딩). `env.py`에 안전한 모델 파일 선택 훅을 추가하고 전용 위치 제어 MJCF에 충돌 비활성 mocap 마커를 포함한다. 이름으로 mocap ID를 찾는다. 시드 기반 2~3m 샘플링, 고정 목표 reset, resample/terminate 모드, 목표 도착 정보 제공.
- [x] 목표 테스트: yaw와 좌표 변환 불변성, π 경계, 시드와 거리, 마커 충돌 없음, 낙상 도착 배제, 기존 목표 보상 계산 후 새 목표 관측·거리 원자 갱신, 경로 용량·수명 제한·reset 초기화. 진척도는 50×거리 감소이며 엄밀한 할인 potential shaping이라고 부르지 않는다.
- [x] 공개 MuJoCo user_scn/mjv_initGeom으로 경로를 표시한다. CSV와 RGB 파일을 저장하고 viewer 실제 실행을 검증한다. 학습/재생에 goal 과제를 연결하며 동일 48차원이더라도 task manifest로 구분한다.
- [x] 전체 회귀, 실제 MuJoCo·Gazebo, 독립 리뷰 및 수정. 절별 가이드·보고서·증거·로컬 커밋과 배포 ZIP/패치.

장시간 학습의 보행·목표 도달 성능은 짧은 기능 검증으로 주장하지 않는다. PPO clipping은 정책 변화의 엄밀한 20% 상한이 아니며 n_envs에 비례한 속도 향상이나 정해진 학습 스텝에서의 보행 성공도 보장하지 않는다.
