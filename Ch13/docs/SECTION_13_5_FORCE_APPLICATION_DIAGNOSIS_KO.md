# Gazebo 명령·접촉 전달 최소 판별 — 2026-11-02

현재 상태는 **원인 판별 진전, 런타임 수정 전**이다. C1 최신 실패267와 G2·연속 성공·Nav2·최종 회귀의 미완료 상태는 그대로다. 전체 로봇 엔진을 새로 실행하지 않았다.

## 판별 결과

1. `force-semantics-0e189460-4aa3-41a8-803e-30bdc3707458`: 중력0, 관성0.1kg·m², 2ms, 자유 회전 관절에서 1Nm를100step 매번 쓰면 Δqd=2.0000000000000013rad/s, 매5step만 쓰면0.4000000000000001rad/s였다. 명령 성분은 Physics 뒤0으로 비워졌고, 쓰지 않은 step의 렌치 축 성분도0이었다. 두 조건 모두110step·서버 소멸 후 정상return0·잔여[]다.
2. 기존 실제 `d50469aa`의2ms contact-event snapshot60개를 읽었다.58개는 capture와 마지막 write 시각 차이가2ms,2개는4ms다. 연속event 간54개 구간은2ms다. 이는 적어도 해당 보존 구간에서 매 physics step 쓰기가 진행됐음을 지지한다. 원본 `force_command`의post-physics0은 이미 소비된 성분이므로 callback 부재의 증거가 아니다. 모든 구간의 호출을 증명하지는 않는다.
3. `constraint-force-8a6fcd90-70ae-4a8c-bedb-991c7440dec9`: 관절 상한에1Nm를 계속 가하면 감쇠 유무 모두qd≈0이고 전달 렌치 축은≈0이다. 관절 제한 반력도 전달 렌치와 actuator effort를 구분해야 하는 사례다. 이 조건은 로봇 바닥 접촉의 대체 증명이 아니다.
4. `contact-force-3563b9ac-b811-4717-a985-56f590885c47`: 관성0.01kg·m², 관절 원점과CoM일치, 중력0, 구면tip/평면 접촉,1Nm 매2ms,1000drive step을 고정했다. 두 조건의 유일한 차이는 native damping0 대10.954451150103322이다. 마지막 qd는−5.9548e−7/−1.8665e−7rad/s로 거의0이지만 전달 렌치는1.0/0.3133928098Nm, 접촉Fz는12.97740345/4.06719702N이다. 단일자유도 `I/(I+hD)=0.3133921658`와 일치하는 감쇠 효과다. 접촉 마찰 때문에 Fz만을`tau/0.1m`라고 단정하지 않으며, 두 조건의 비율을 비교한다. 각1010step·서버 소멸 후 정상return0·잔여[]다.

## 실제 실패 모델과의 오프라인 대조

DART6.13.2 공개 API로 원본 URDF와 실패267의q/pose/contact point/force를 읽어 전체26자유도M과J를 계산했다. 로봇 엔진·제어기는 실행하지 않았다. M의최소고유값0.0004597387, 선형해 residual4.29e−14, 질량15.2101kg이다. 첫 `DartLoader` 기본값은 질량 없는 광학frame2개에 각각1kg/기본관성을 넣어17.2101kg이 됐다. 이 준비 차이를 발견한 첫 `dadf9408` 결과를 보존하고 채택하지 않았다. `7d150460`은 기본관성0과 원래 질량15.2101kg 가드를 사용했다. 외부 설치나 URDF를 바꾸지 않았다.

접촉을 포함한 실제 순서에서 정상 순가속도0을 가정하면 다음 관계를 진단 가설로 얻는다. 일반화 좌표 전체에서D는 관절 감쇠 행렬이고 floating root는0이다.

```
a_free = (M+hD)^−1 (u−g−Dv)
0 = a_free + M^−1 JᵀF
u = g−JᵀF + Dv − hD M^−1 JᵀF
```

이는 `u=g−JᵀF+Dv`만 쓰는 연속 정역학 모델과 다르다. 임의의4배 계수가 아니며 M·J·D 전체에 의존한다. 중력 포함 자유가속도와 접촉 충격량을 순차 처리하는 계산에 관한 식이고 모든 순간의 정확한 동역학 식이라고 주장하지 않는다.

`implicit-damping-comparison-bd4be4a1-7dd8-4ff7-90a2-ec3254ca8f3b.json`에서 FL calf의 연속 정역학은−7.61151453Nm, 추가 암시적 항은−22.61643306Nm, Dv는+0.22698467Nm라 명령 예측은−30.00096292Nm이다. 실제 native command는−30Nm이다.12개 다리 관절의 최대 명령 잔차는 연속식22.61547014Nm, 암시적 항 포함0.00412730Nm다. 부모 기하는53.130s, 대조 native 상태는53.124s여서6ms 차이가 있으며 정상 순가속도·작은 속도편향 가정도 남는다. 이 오차를 런타임 허용 여유로 채택하지 않는다.

## 공식 구현 근거

- [Gazebo sim8 Physics](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc): JointForceCmd→SetForce와성분정리.
- [gz_ros2_control1.2.20](https://github.com/ros-controls/gz_ros2_control/blob/1.2.20/gz_ros2_control/src/gz_ros2_control_plugin.cpp): PreUpdate manager.write, 제어주기의read/update.
- [DART GenericJoint](https://github.com/dartsim/dart/blob/v6.13.2/dart/dynamics/detail/GenericJoint.hpp): 암시적 투영관성M+hD와 감쇠력의속도·자유가속도 항. 실제 설치헤더는 `/opt/ros/jazzy/opt/gz_dartsim_vendor/include/dart/dynamics/detail/GenericJoint.hpp`다.
- [gz-physics DART JointFeatures](https://github.com/gazebosim/gz-physics/blob/gz-physics7/dartsim/src/JointFeatures.cc): SetJointForce는DART FORCE/command, 전달 렌치는child BodyForce를joint frame으로 변환한다.

## 다음 작업과 보존

현재 nativeXYZ는 `J diag(1/Kp) Jᵀ`인 발별 독립 compliance로 힘 응답을 예측하고, 물리 토크는g−JᵀF로 검사한다. 위의 접촉·암시적 감쇠 관계가 그 모델에 빠져 있다. 다음 단계는 **현재물리·게인·native damper·토크cap·단일소유권·원래 기한을 유지한 채** 전체M과 관절 결합을 포함한 힘 응답을 오프라인에서 독립 검증하는 것이다. 고정배수·Kp조정·외부DART 수정·원래 실패관측의 infeasible을 억지PASS로 바꾸는 방법은 쓰지 않는다. 그 뒤 명시적GazeboG2 경로만 최소수정/회귀하고 고정본G1/C1으로 돌아간다.

세 최소 물리 실행은 모두 서비스·시계·tick·드라이버를 바꾸지 않았다. 각 명령·소스SHA·binary SHA·작은csv·stderr·manifest는evidence에 있다. 소스가 후속계측으로 바뀐 경우 초기버전을 복원해 **당시 SHA와 일치할 때만**`source/`에 보존했다.5개 실행 모두 입력source누락0이며 `task8-force-semantics-retention.json`에 기록했다. 네이티브binary/build는원위치에 유지하고 Windows에는작은결과만 복사했다. 설치된런타임 패키지·고정소스는아직바뀌지 않았다.
