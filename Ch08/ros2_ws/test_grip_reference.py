import mujoco
import mujoco.viewer
import time
import numpy as np

# 1. 모델 및 데이터 로드
# (주의: 사용 중이신 XML 파일명으로 변경하여 사용하셔도 됩니다.)
model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/minimal_gripper.xml")
data = mujoco.MjData(model)

def step_sim_until_stable(viewer, total_steps, delay=0.002):
    """지정된 스텝만큼 시뮬레이션을 전진시키고 뷰어를 동기화합니다."""
    for _ in range(total_steps):
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(delay)

# debugging report: States diagnostic
def print_diagnostic_report(model, data, step_name):
    """
    진단을 위해 필요한 로봇과 물체의 상태 로그를 출력하는 레포트 함수
    """
    print(f"\n📊 ==================== [디버깅 리포트: {step_name}] ====================")
    
    # 1. 물체(Cube) 정보 추출
    cube_pos = None
    try:
        cube_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
        cube_pos = data.xpos[cube_id]
        print(f"[물체 상태] Cube 중심 위치   (X, Y, Z) : {cube_pos[0]:.4f}, {cube_pos[1]:.4f}, {cube_pos[2]:.4f}")
    except Exception:
        print("[물체 상태] 'cube' 바디를 찾을 수 없습니다.")

    # 2. 그리퍼 기준점(grasp_site 또는 TCP) 정보 추출
    site_pos = None
    try:
        # 사용 중이신 모델의 노란 구슬 site 이름("grasp_site" 등)으로 확인하세요.
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")
        site_pos = data.site_xpos[site_id]
        print(f"[그리퍼]   grasp_site 위치 (X, Y, Z) : {site_pos[0]:.4f}, {site_pos[1]:.4f}, {site_pos[2]:.4f}")
    except Exception:
        # 레퍼런스 코드용 예외 처리 (암 베이스 위치로 대체 가능)
        try:
            arm_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm")
            site_pos = data.xpos[arm_id]
            print(f"[그리퍼]   Arm Base 위치   (X, Y, Z) : {site_pos[0]:.4f}, {site_pos[1]:.4f}, {site_pos[2]:.4f} (Site 없음)")
        except Exception:
            pass

    # 3. 핵심 오차 진단 연산 (Z축 오프셋 분석)
    if cube_pos is not None and site_pos is not None:
        z_offset_error = site_pos[2] - cube_pos[2]
        print(f"💡 [진단] 큐브 중심과 그리퍼 기준점 간의 Z축 높이 차이: {z_offset_error:.4f} m")
        
        # 공식 문서 기준 매칭 조건 진단
        if abs(z_offset_error) < 0.01:
            print("🟢 진단 결과: 정렬 정상 (그리퍼 중심이 큐브 뱃속 정중앙에 위치함)")
        elif z_offset_error > 0.01:
            print(f"🔴 진단 결과: 높이 오차 발생 (그리퍼가 큐브보다 {z_offset_error*100:.1f}cm 높게 떠 있습니다!)")
        else:
            print(f"🔵 진단 결과: 깊이 오차 발생 (그리퍼가 큐브보다 {abs(z_offset_error)*100:.1f}cm 너무 낮게 박혀 있습니다)")

    # 4. 제어 신호 및 관절 값 출력
    print(f"[액추에이터] 현재 제어 입력값 (data.ctrl) : {list(np.round(data.ctrl, 4))}")
    print(f"[관절 공간] 현재 관절 위치값 (data.qpos) : {list(np.round(data.qpos, 4))}")
    print("====================================================================\n")

# debugging report: Contacts Position
def print_contact_report(model, data):
    print("\n========== Contact Report ==========")
    print(f"Number of Contacts : {data.ncon}")

    for i in range(data.ncon):
        contact = data.contact[i]
        geom1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom1)
        geom2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom2)
        print(f"[{i}] {geom1} <--> {geom2}")
        # Contact Position
        print("Contact Position :", np.round(contact.pos,4))

# debugging report: Constraint Forces
def print_force_report(data):
    print("\n========== Joint Force ==========")
    print("Actuator")
    print(np.round(data.qfrc_actuator,3))
    print("Constraint")
    print(np.round(data.qfrc_constraint,3))
    print("Passive")
    print(np.round(data.qfrc_passive,3))


# 수동 시퀀스 제어 메인 루프
with mujoco.viewer.launch_passive(model, data) as viewer:
   
    # -------------------------------------------------------------
    # STEP 1: 초기 대기 상태
    # -------------------------------------------------------------
    data.ctrl[0] = 0.0  # Lift Lift 관절 대기
    data.ctrl[1] = 0.0  # 좌측 손가락 오픈
    data.ctrl[2] = 0.0  # 우측 손가락 오픈
    step_sim_until_stable(viewer, 400)

    # debugging report 출력
    print_diagnostic_report(model, data, "1. Initial State (대기)")

    input("👉 [STEP 1 완료] MuJoCo 뷰어에서 정렬 상태를 마우스로 확인하신 후, [Enter]를 누르면 다음 단계(Approach)로 진행합니다...")

    # -------------------------------------------------------------
    # STEP 2: Pick 자세 확인 단계 (핵심 디버깅 구간)
    # -------------------------------------------------------------
    # data.ctrl[0] = -0.32
    data.ctrl[0] = -0.25 # 목표 Pick 위치로 하강 (사용하시는 환경에 맞게 조절)
    step_sim_until_stable(viewer, 800)
    
    # debugging report 출력
    print_diagnostic_report(model, data, "2. ENTER : Pick 자세 확인")
    print("💡 [팁] 이 상태에서 뷰어의 렌더링 옵션(Visual Off / Collision On)을 설정해 노란 구슬의 위치를 눈으로 대조하세요.")
    left_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "left_finger")
    right_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "right_finger")
    arm_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm")
    cube_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
    print("(xpos) Arm         :", data.xpos[arm_id])
    print("(xpos) Left Finger :", data.xpos[left_id])
    print("(xpos) Right Finger:", data.xpos[right_id])
    print("(xpos) Cube        :", data.xpos[cube_id])

    input("👉 [STEP 2 완료] 리포트 데이터와 뷰어의 구슬 위치를 분석한 후, [Enter]를 누르면 그리퍼를 닫습니다(Grip)...")

    # -------------------------------------------------------------
    # STEP 3: Gripping (물체 파지 상태)
    # -------------------------------------------------------------
    data.ctrl[1] = 0.03  # 손가락 압착 제어 신호 인가
    data.ctrl[2] = 0.03 
    step_sim_until_stable(viewer, 600)
    
    # debugging report 출력
    print_diagnostic_report(model, data, "3. Grip (손가락 닫힘 완료)")
    print_contact_report(model, data)
    print_force_report(data)
    left = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"left_finger")
    right = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"right_finger")
    print("(xpos) left_finger : ", data.xpos[left])
    print("(xpos) right_finger: ", data.xpos[right])

    input("👉 [STEP 3 완료] 손가락 면이 큐브에 제대로 밀착되었는지 확인 후, [Enter]를 누르면 들어올리기(Lift)를 시작합니다...")

    # -------------------------------------------------------------
    # STEP 4: Lift (들어올리기 및 슬립 여부 확인)
    # -------------------------------------------------------------
    data.ctrl[0] = 0.1  # 제어 신호를 위로 상승 유도
    step_sim_until_stable(viewer, 1200)
    
    # debugging report 출력
    print_diagnostic_report(model, data, "4. Lift (들어올리기 완료)")
    print_contact_report(model, data)
    print_force_report(data)
    
    print("🏁 모든 단계별 테스트가 종료되었습니다. 시뮬레이터 창을 닫아주세요.")
    