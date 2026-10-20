# 1.5절 패키지 계약 정적 테스트 및 수정 보고서

- 기존 검토: `SECTION_1_5_REPORT_KO.md`의 `C01-15-01`~`C01-15-07`
- 판정: **STATIC_PASS (4/4) / ROS2_BUILD_NOT_RUN**
- 파일: `Ch01/tests/test_ch01_package_contract.py` (신규)

## 수정 방침

`my_robot_controller`는 **원고 1.5에서 패키지를 막 생성한 단계**와 **1.6의 완성 단계**를 하나의 저장소에 나타낸다. `setup.py`의 현재 `test_node`를 `simple_controller`로 되돌리면 1.6절이 깨지므로 기존 공개 API를 유지했다. 대신 실제 코드·설정이 흔히 어긋나는 지점을 잡도록 **ROS 2 없이 실행하는 정적 계약 회귀 테스트**를 추가했다. 제3자 ROS 2 examples 벤더 소스는 편집하지 않았다.

## 실행 시험 결과

| 검증 내용 | 판정 |
|---|---|
| `package.xml`: 이름, `ament_python`, `rclpy` | **PASS** |
| `setup.py`: `test_node = my_robot_controller.simple_controller:main` | **PASS** |
| `setup.cfg`: `lib/my_robot_controller` | **PASS** |
| 진입점 모듈·`main`·`timer_callback`·resource 존재, AST 유효 | **PASS** |
| `python3 -m compileall -q Ch01/tests` | **PASS** |
| `colcon build` / `ros2 run` | **NOT_RUN** |

## 재현 명령

```bash
python3 -m unittest discover -s Ch01/tests -p test_ch01_package_contract.py -v
python3 -m compileall -q Ch01/tests
```

**중요:** 테스트는 메타데이터 **계약 일치 여부**만 확인한다. 실제 Python 패키지 설치·DDS 실행은 Jazzy 워크스페이스에서 확인해야 한다. 원고의 `--node_name`은 `--node-name`, `source install/setup.`은 `source install/setup.bash`로 가이드에서 교정되어 있으며, 책 원고 파일에 대한 수정은 이 브랜치에서 수행하지 않는다.

## 후속 작업

- 패키지 Description/License TODO 등은 1.7절에 속하며 소유자의 라이선스 결정은 임의로 대행하지 않는다.
- 후속 PR 병합 시 `Ch01/tests` 아래 1.6/1.7 테스트를 함께 실행한다.
