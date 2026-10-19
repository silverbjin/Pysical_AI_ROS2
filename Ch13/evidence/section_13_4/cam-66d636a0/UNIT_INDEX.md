# 빌드·시험 원본 색인

`auto-camera-red.log`는 전원 종료로 중단된 부분 로그다. 완결된 RED는
`auto-camera-red-restart.log`(10실패), GREEN은 `auto-camera-green.log`(40통과)다.
`auto-camera-build.log`는5패키지 빌드, `auto-camera-suite.log`/`pytest.xml`은276소스시험이다.
`auto-camera-colcon.log`는5패키지 시험 실행, `auto-camera-result-current.log`는123건의
현재 결과 집계다. `auto-camera-result.log`의155는 과거 보관 사본32건이 섞인 최초 집계로,
새 시험 개수로 인정하지 않는다. `installed.json`은 실제5패키지·두라이브러리 설치 감사다.

아래 짧은 이름은 Windows Git 경로 제한을 피하기 위한 원본 바이트 사본이다.
원래 기준 폴더: `Ch13/ros2_ws/build13_4_snapshot_full_35954ef5/`.

| 사본 | 원래 상대 경로 |
|---|---|
| p001.xml | integrated_robot_camera/test_results/integrated_robot_camera/test_plugin_loading.gtest.xml |
| p002.xml | integrated_robot_camera/test_results/integrated_robot_camera/test_snapshot_camera_plugin.gtest.xml |
| p003.xml | integrated_robot_camera/test_results/integrated_robot_camera/test_snapshot_mailbox.gtest.xml |
| p004.xml | integrated_robot_description/test_results/integrated_robot_description/copyright.xunit.xml |
| p005.xml | integrated_robot_description/test_results/integrated_robot_description/flake8.xunit.xml |
| p006.xml | integrated_robot_description/test_results/integrated_robot_description/lint_cmake.xunit.xml |
| p007.xml | integrated_robot_description/test_results/integrated_robot_description/pep257.xunit.xml |
| p008.xml | integrated_robot_description/test_results/integrated_robot_description/xmllint.xunit.xml |
| p009.xml | integrated_robot_runtime/pytest.xml |
| p010.xml | integrated_robot_vision/pytest.xml |

인터페이스 패키지는 별도 XML이 없으며 빌드 및 생성물/설치 일치를 별도로 확인했다.
