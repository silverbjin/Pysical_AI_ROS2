# 4.3절 코드 수정·정적 테스트 보고서 (2026-10-21 KST)

- 브랜치: `feat/ch04-section-4-3`; 코드 변경 SHA: `ba74828898c1fa5109bd6797fcea6a0405cde191`
- 리뷰: [SECTION_4_3_REPORT_KO.md](SECTION_4_3_REPORT_KO.md)
- 판정: **STATIC_CONTRACT_PASS 6/6**, 실제 타이머 주기/RViz 실행 **NOT_RUN**

## 수정 및 원인

원본은 타이머가 호출될 때마다 `theta+=0.05`로 갱신했으므로 실행 지연에 따라 각속도가 달라졌다. `dynamic_tf_broadcaster.py`는 **ROS clock의 nanoseconds 차이**로 `dt`를 계산하고 `angular_speed=1.5 rad/s`를 적용한다. backwards clock jump를 무시하고 한 콜백의 `dt`를 0.25초 이하로 제한한다(장기 스케줄링 정확성을 보장하는 정책은 아님). `trajectory_math.py`로 원운동 위치·접선각·xyzw 쿼터니언 수식을 분리했다. 테스트 파일 `test_section_4_3_motion.py`에 반경 불변, 90도 회전, 쿼터니언 정규화, 비정상 반경, 코드 시간 계약 검사 등 5개 케이스를 작성했다.

## 원격 소스 기반 정적 검사

| 항목 | 결과 |
|---|---|
| elapsed ROS time | PASS |
| backward clock protection | PASS |
| bounded time jump | PASS |
| tangent yaw | PASS |
| unit quaternion | PASS |
| unit test coverage | PASS |

이 PASS는 GitHub에 저장된 텍스트의 계약 검사를 뜻하며, 작성된 `unittest`와 ROS 실행 검증은 아직 수행하지 않았다.

## 재현 명령

```bash
cd Ch04/ros2_ws/src/my_robot_tf
PYTHONPATH="$PWD" python3 -m unittest discover -s test -p 'test_section_4_3_motion.py' -v
python3 -m compileall -q my_robot_tf/dynamic_tf_broadcaster.py my_robot_tf/trajectory_math.py
# Jazzy 환경
colcon build --packages-select my_robot_tf
ros2 run my_robot_tf dynamic_tf_broadcaster
ros2 topic hz /tf
ros2 run tf2_ros tf2_echo world turtle_frame
```

**예측:** 반지름 2m, 공칭 각속도 1.5rad/s, 한 바퀴 약 4.19초. 이는 측정치가 아니다. `clock jump`·`ROS_DOMAIN_ID`·DDS 지연과 주파수는 실제 런타임 로그로 평가한다.

| 검증 종류 | 상태 |
|---|---|
| 원격 구조 계약 | **PASS 6/6** |
| Python unittest·compile | **NOT_RUN** |
| colcon·TF topic Hz·RViz | **NOT_RUN** |

회귀 위험: 예전 fixed-step 시간 모델과 출력 위상이 달라진다. 4.4절 listener에서 실제 시간 처리와 최신값 조회를 재확인한다.
