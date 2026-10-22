# SECTION 3.3 — Xacro 매크로·관성·변환 리뷰 보고서

- 원고 범위: 3.3.1~3.3.3, Xacro 변수·매크로·관성 계산·변환
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20 KST
- 판정: **정적 수정 완료 / Xacro 실행·동역학 실험 미검증**

## 핵심 버그·수정
| ID | 심각도 | 근거 | 변경 |
|---|---|---|---|
| 3.3-01 | High | `box_inertia(m,w,h,d)`에서 링크의 긴 Z축 `h`를 누락한 `Iyy`, 긴 축을 반영한 잘못된 `Izz` | `Ixx=m(h²+d²)/12`, `Iyy=m(w²+h²)/12`, `Izz=m(w²+d²)/12`로 수정 |
| 3.3-02 | High | 매크로 `box_inertia` / `cylinder_inertia`가 관성 중심 `origin` 미설정 | 중심 Z=h/2 설정; visual·collision과 질량 중심 일치 |
| 3.3-03 | Medium | 3.2 정적 `two_dof_arm.urdf`에는 고정 EE가 있지만 Xacro에는 없음 | `joint_ee` 및 `end_effector_link` 추가 |
| 3.3-04 | Medium | 저장소의 `two_dof_arm_generated.urdf`는 Xacro의 이전 스냅샷으로 Gazebo 플러그인 및 EE가 누락됨 | 역사적 샘플로 남기되 재사용 **금지**; 아래 명령으로 반드시 새로 생성 |
| 3.3-05 | Info | `xacro:box_inertia`의 `h`는 긴 Z축, `w,d`는 서로 직교하는 짧은 축 | 명칭과 좌표축 대응을 실습에 명확히 정의 |

**수정 후 계산 예상치**:
- `link1`, `link2`: m=1kg, 너비=깊이=0.05m, 길이=0.5m → `Ixx=Iyy=0.0210416667`, `Izz=0.0004166667` kg·m², CoM Z=0.25m.
- `base_link`: m=10kg, r=0.1m, h=0.1m → `Ixx=Iyy=0.0333333333`, `Izz=0.05` kg·m², CoM Z=0.05m.

## 검증 구분
- **PASS (텍스트 검사)**: 관성 수식의 축 교정, `origin` 추가, EE 부모·자식 링크 이름 일치, 기존 2개 모터 joint 이름 유지.
- **NOT RUN**: Xacro 전처리·check_urdf 파싱, 동역학 안정성, Gazebo 플러그인 로딩, 조인트 위치 제어. 환경에 ROS가 없어서 PASS 주장 불가.

## 재현
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-xacro liburdfdom-tools
xacro src/my_robot_description/urdf/two_dof_arm.urdf.xacro > /tmp/ch03_3_3_generated.urdf
check_urdf /tmp/ch03_3_3_generated.urdf
grep -E 'joint_ee|end_effector_link' /tmp/ch03_3_3_generated.urdf
```
`check_urdf`는 구문/트리만 확인하므로 정량적인 물리 안정성은 3.8 제어 실험에서 검증한다. **주의**: 원래 커밋에 있는 `two_dof_arm_generated.urdf`는 소스와 동기화된 결과물이 아니다. 항상 Xacro에서 직접 생성한 `/tmp` 파일을 기준으로 한다.

## 합격 기준
Xacro 명령 exit 0, URDF 파서 exit 0, 4 링크/3 조인트, `end_effector_link` 관측. 이후 Gazebo 가동 시 비정상 폭주 없고 joint1·2 실측 위치가 명령값에 수렴하는지 로그 증거가 필요하다. Acceptance=`PENDING_RUNTIME_VERIFICATION`.
