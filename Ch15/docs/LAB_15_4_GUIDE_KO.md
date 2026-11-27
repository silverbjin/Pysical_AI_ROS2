# 15.4 협업 개발 실습 (G05)
목표: 브랜치, PR, 충돌, 고정 의존성을 실습한다. 실제 프로젝트 main은 수정하지 않는다.
1. `bash Ch15/scripts/g05_git_lab.sh`: 임시 bare remote에서 두 브랜치의 충돌을 확인하고 해결한다. 소형 생성 파일의 LFS pointer 및 fsck를 확인한다.
2. `python3 Ch15/python/g05_lock.py Ch15`: 승인된 URL과 40자리 SHA를 비교한다. .repos import는 검증용 로컬 전용이며 mock은 외부 모델이 필요 없다. 실제 자산은 승인된 94개 closure만 prepare_assets.sh로 가져온다.
3. ROS Jazzy 환경에서 `rosdep install --from-paths Ch15/ros2_ws/src --ignore-src --rosdistro jazzy -y`, 별도 workspace에서 colcon build/test. Python 의존성과 apt 의존성은 섞지 않는다. CI dpkg inventory로 확인한다.
4. PR_TEMPLATE.md를 사용해 RED/GREEN과 검수 범위를 기록한다. G06 read-only visualization DDS 및 설치 검증 PASS.

5. 실제 [PR #207 CI 사례](reports/CI_DEBUG_CASE_STUDY_KO.md)를 읽고, sparse checkout과 import dependency가 일치하는지 검토한다.

## G09 공통 실행 경로
Ch15 루트, `CH15_SOURCE_SHA`를 실제 고정 HEAD로 설정하고 `bash scripts/run_lab.sh 15.4 --guide` 실행. 상세 선행 환경과 evidence archive는 [15.9](LAB_15_9_GUIDE_KO.md) 참조. 문서 조회와 실제 실행을 구분한다.
