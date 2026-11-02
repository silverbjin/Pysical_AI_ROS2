# SECTION 3.5 — Visual / Collision / Inertial 모델링 감사

- 원고: 3.5.1~3.5.4 (STL·DAE, 단순 충돌체, 질량/관성, Blender)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20
- 점검 대상: `urdf/simple_arm.urdf`, `urdf/two_dof_arm.urdf`, `urdf/two_dof_arm.urdf.xacro`, `meshes/link_*.stl`
- 판정: **소스 구조 정적 검토 완료 / 동역학·메시 품질 미검증**

## 발견 및 선행 PR
| ID | 심각도 | 발견 | 처리 |
|---|---|---|---|
| 3.5-01 | High | `two_dof_arm.urdf`의 `link1` visual이 Y=1.5708rad 회전하지만 collision은 Z축 | **3.2절 브랜치**에서 수정; 병합 전에는 본 절 품질 점검 실패 |
| 3.5-02 | High | `two_dof_arm.urdf.xacro`의 CoM 누락 및 관성 축 수식 오류 | **3.3절 브랜치**에서 수정; 병합 전에는 동역학 정확도 보장 불가 |
| 3.5-03 | Medium | `meshes/`에는 STL 3개가 있지만 기본 모델은 box/cylinder을 사용하며 STL 경로는 주석 | STL 시각화는 선택적 심화 실습으로 구분 |
| 3.5-04 | Low | STL 2개(`link_1.stl`, `link_2.stl`)가 동일 Git blob; 실질적으로 같은 메시 | 모델이 동일한 링크를 재사용하려는 의도인지 확인 필요. 원고 설명만으로 단정할 수 없음 |
| 3.5-05 | Info | STL/DAE 메시는 렌더링/충돌에 쓰일 수 있으나 **URDF→MuJoCo가 완전히 호환된다는 뜻은 아님** | 시뮬레이터별 모델 변환과 관성 지원 확인 필요 |

이 절은 **별도 기능 패치 대신 3.2·3.3 선행 수정에 의존**한다. 같은 파일을 다시 중복 수정하지 않아 PR 충돌을 피한다.

## 물리 수치 검증 요건
균질 상자: `Ixx=m(y²+z²)/12`, `Iyy=m(x²+z²)/12`, `Izz=m(x²+y²)/12`. 원기둥(Z 중심축): `Ixx=Iyy=m(3r²+h²)/12`, `Izz=mr²/2`. 시각 모델·충돌체 모두 외형을 정의하지만 CoM·관성은 운동방정식에 별도 입력된다.

## 검증 범위
- **PASS(정적)**: geometry와 STL 경로가 주석인지, 원고–코드 구성이 어떻게 다른지 확인.
- **BLOCKED(선행 수정 미병합)**: visual/collision 방향 및 CoM 일치 검증을 3.2·3.3 합류 전에는 PASS로 표기 금지.
- **NOT RUN**: 실제 Gazebo 접촉·침투 테스트, 성능 프로파일링, Blender 메시 검사.

## 실행 시 확인
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
check_urdf src/my_robot_description/urdf/two_dof_arm.urdf
xacro src/my_robot_description/urdf/two_dof_arm.urdf.xacro > /tmp/ch03_3_5.urdf
check_urdf /tmp/ch03_3_5.urdf
```
3.2+3.3을 병합한 테스트 브랜치에서 확인한 뒤 GUI에서 Collision 표시와 Visual 정렬을 캡처한다. Acceptance=`BLOCKED_BY_3_2_AND_3_3_FOR_RUNTIME`.
