import gymnasium as gym
from gymnasium import spaces
import numpy as np
import mujoco
import os

class ReachEnv(gym.Env):
    """
    3자유도 로봇 팔이 목표 지점(빨간 구)에 도달하도록 학습하는 환경 (물리 정합성 수정본)
    """
    metadata = {"render_modes": ["human"], "render_fps": 100}

    def __init__(self, render_mode=None):
        super(ReachEnv, self).__init__()
        
        # 1. 모델 로드 (가장 안전한 절대 경로 기법 유지)
        # xml_path = os.path.join(os.path.dirname(__file__), "assets", "simple_arm_3dof.xml")
        # xml_path = os.path.join(os.path.dirname(__file__), "src/my_robot_description/assets", "simple_arm_3dof.xml")
        xml_path = os.path.join(os.path.dirname(__file__), "src/my_robot_description/assets", "simple_arm_6dof.xml")
        if not os.path.exists(xml_path):
             raise FileNotFoundError(f"XML File not found: {xml_path}")

        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        
        if render_mode not in (None, "human"):
            raise ValueError("ReachEnv currently supports only human rendering")
        self.render_mode = render_mode
        self.viewer = None

        # [최적화] API 오버헤드 방지를 위한 바디 및 조인트 ID 사전 캐싱
        self.ee_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "link_ee")
        self.target_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "target")
        if self.ee_id < 0 or self.target_id < 0:
            raise ValueError("MJCF missing link_ee or target body")
        self.target_mocap_idx = int(self.model.body_mocapid[self.target_id])
        if self.target_mocap_idx < 0:
            raise ValueError("target must be a MuJoCo mocap body")
        self.max_episode_steps = 500
        self._elapsed_steps = 0

        # 2. Action Space: 3개 관절의 토크 정규화 범위 (-1.0 ~ 1.0)
        # self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        # 변경 (안전한 동적 가변형 구조)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.model.nu,), dtype=np.float32)

        # 3. Observation Space: 12차원 [qpos(3), qvel(3), target_pos(3), dist_vec(3)]
        # self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(12,), dtype=np.float32)
        # 기존: qpos(3) + qvel(3) + ee_pos(3) + target_pos(3) = 12차원
        # 변경: qpos(6) + qvel(6) + ee_pos(3) + target_pos(3) = 18차원
        obs_dim = self.model.nq + self.model.nv + 3 + 3
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
        
        # 기본 초기화 상태 백업
        self.init_qpos = self.data.qpos.ravel().copy()
        self.init_qvel = self.data.qvel.ravel().copy()

    # def reset(self, seed=None, options=None):
    #     super().reset(seed=seed)
        
    #     # 물리 상태 복사 및 초기화
    #     qpos = self.init_qpos.copy()
    #     qvel = self.init_qvel.copy()
        
    #     qpos[:3] += self.np_random.uniform(low=-0.1, high=0.1, size=3)
    #     qvel[:3] += self.np_random.uniform(low=-0.005, high=0.005, size=3)
        
    #     while True:
    #         # X, Y, Z 모든 축에 대해 무작위로 목표 위치를 샘플링하는가?
    #         target_pos = self.np_random.uniform(low=[-0.4, -0.4, 0.1], high=[0.4, 0.4, 0.5])
    #         if np.linalg.norm(target_pos) < 0.5:
    #             break
        
    #     qpos_adr = self.model.jnt_qposadr[self.target_jnt_id]
    #     qpos[qpos_adr:qpos_adr+3] = target_pos
        
    #     self.data.qpos[:] = qpos
    #     self.data.qvel[:] = qvel
    #     mujoco.mj_forward(self.model, self.data)
        
    #     # [교정] Sim-to-Real 심화: 에피소드 시작 시 이전 에피소드의 액션 잔재를 완전히 지웁니다.
    #     self.last_action = np.zeros(self.model.nu, dtype=np.float32)
        
    #     return self._get_obs(), {}
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self._elapsed_steps = 0
        
        # 1. 로봇 관절 물리 상태 복사 및 초기화 (독립된 qpos, qvel)
        qpos = self.init_qpos.copy()
        qvel = self.init_qvel.copy()
        
        # 로봇 관절 초기화에 약간의 노이즈 주입
        # qpos[:3] += self.np_random.uniform(low=-0.1, high=0.1, size=3)
        # qvel[:3] += self.np_random.uniform(low=-0.005, high=0.005, size=3)
        # 변경
        qpos[:self.model.nq] += self.np_random.uniform(low=-0.1, high=0.1, size=self.model.nq)
        qvel[:self.model.nv] += self.np_random.uniform(low=-0.005, high=0.005, size=self.model.nv)
        
        
        
        # 2. 목표 지점(붉은 공)의 새로운 3차원 랜덤 좌표 생성
        while True:
            # X, Y, Z 모든 축에 대해 무작위로 목표 위치를 샘플링
            target_pos = self.np_random.uniform(low=[-0.4, -0.4, 0.1], high=[0.4, 0.4, 0.5])
            if np.linalg.norm(target_pos) < 0.5:
                break
        
        # 로봇 관절 상태 데이터를 시뮬레이션 버퍼에 먼저 주입
        self.data.qpos[:] = qpos
        self.data.qvel[:] = qvel
        
        # 3. [교정] jnt_qposadr 방식을 완전 배제하고 mocap_pos API로 직접 텔레포트
        # XML에 등록된 'target' 이라는 이름을 가진 모캡 바디의 고유 ID를 안전하게 조회합니다.
        mocap_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "target")
        
        # 해당 모캡 바디의 실제 주소 인덱스(body_mocapid)를 참조하여 3차원 좌표를 덮어씁니다.
        target_mocap_idx = self.target_mocap_idx
        self.data.mocap_pos[target_mocap_idx] = target_pos
        
        # 4. 바뀐 상태 정보(로봇 관절 + 모캡 위치)를 시뮬레이션 물리 세계에 즉시 전방 반영
        mujoco.mj_forward(self.model, self.data)
        
        # Sim-to-Real 심화: 에피소드 시작 시 이전 에피소드의 액션 잔재를 완전히 제거
        self.last_action = np.zeros(self.model.nu, dtype=np.float32)
        
        return self._get_obs(), {}


    def step(self, action):
        action = np.asarray(action, dtype=np.float64)
        if action.shape != self.action_space.shape or not np.all(np.isfinite(action)):
            raise ValueError("Invalid action shape or nonfinite action")
        action = np.clip(action, self.action_space.low, self.action_space.high)
        self.data.ctrl[:] = action 
        
        for _ in range(5):
            mujoco.mj_step(self.model, self.data)
            
        obs = self._get_obs()
        ee_pos = self.data.xpos[self.ee_id]
        target_pos = self.data.xpos[self.target_id]
        
        # 보상 계산 (이 시점의 self.last_action은 '이전 스텝'의 값임이 명확히 보장됨)
        # reward, reward_info = self.compute_reward(ee_pos, target_pos, action)
        # [수정] compute_reward -> calculate_reward로 변경
        reward, reward_info = self.calculate_reward(ee_pos, target_pos, action)
        
        # [교정] 보상 계산이 완전히 끝난 후, 다음 스텝을 위해 비로소 현재 액션을 '이전 액션'으로 백업
        self.last_action = action.copy()
        
        # terminated = reward_info["is_success"]
        # [교정] NumPy bool 구조가 섞이지 않도록 명시적으로 파이썬 네이티브 bool 타입으로 변환
        terminated = bool(reward_info["is_success"])
        self._elapsed_steps += 1
        truncated = bool(self._elapsed_steps >= self.max_episode_steps and not terminated)

        if self.render_mode == "human":
            self.render()

        return obs, reward, terminated, truncated, reward_info

    # def _get_obs(self):
    #     # 안전한 슬라이싱을 통한 12차원 핵심 피처 가공
    #     qpos = self.data.qpos[:3].astype(np.float32)
    #     qvel = self.data.qvel[:3].astype(np.float32)
        
    #     target_pos = self.data.xpos[self.target_id].astype(np.float32)
    #     ee_pos = self.data.xpos[self.ee_id].astype(np.float32)
    #     dist_vec = target_pos - ee_pos
        
    #     return np.concatenate([qpos, qvel, target_pos, dist_vec])
    
    def _get_obs(self):
    # 기존의 [:3] 슬라이싱을 제거하고 모든 관절의 위치/속도를 다 가져옵니다.
        return np.concatenate([
            self.data.qpos[:self.model.nq],  # 6개 관절 각도
            self.data.qvel[:self.model.nv],  # 6개 관절 속도
            self.data.site('ee_site').xpos,  # 말단 장치 3D 좌표
            self.data.mocap_pos[self.target_mocap_idx]  # 목표물 3D 좌표
        ]).astype(np.float32)
    

    def render(self):
        # if self.viewer is None:
        #     import mujoco.viewer
        #     self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        # self.viewer.sync()        
        if self.render_mode == "human":
            if self.viewer is None:
                # 뷰어가 처음 켜질 때 모델과 데이터를 연동하여 비동기 실행
                import mujoco.viewer
                self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
            
            # [★ 중요] 이 싱크 명령어가 수행되어야 바뀐 공의 위치가 창에 그려집니다.
            self.viewer.sync()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()

    # def compute_reward(self, ee_pos, target_pos, action):
    def calculate_reward(self, ee_pos, target_pos, action):
        """
        보상 함수 심화 구현 (Sim-to-Real 부드러움 제어 추가 항 반영)
        """
        # 1. 거리 보상
        distance = np.linalg.norm(ee_pos - target_pos)
        w_dist = 1.0
        r_dist = -distance 

        # 2. 제어 비용 (Action L2 Regularization)
        w_ctrl = 0.01   # 너무 크면 안 움직이고, 너무 작으면 털털 텁니다.
        r_ctrl = -np.sum(np.square(action))
        
        # 3. [추가] Sim-to-Real을 위한 부드러움 제어 페널티 (Action Derivative Penalty)
        # 가중치는 과도한 주객전도를 막기 위해 0.05 수준으로 작게 제어합니다.
        w_smooth = 0.05 # 이전 액션과의 차이를 억제하여 곡선 흐름을 만듭니다.
        r_smooth = -np.sum(np.square(action - self.last_action))
        
        # 4. 성공 보너스
        threshold = 0.05
        r_bonus = 10.0 if distance < threshold else 0.0
        
        # 5. 접촉 페널티
        w_contact = 0.01
        r_contact = -float(self.data.ncon)
        
        # 총 보상 계산
        total_reward = ((w_dist * r_dist) + 
                        (w_ctrl * r_ctrl) + 
                        (w_smooth * r_smooth) + 
                        r_bonus + 
                        (w_contact * r_contact))
        
        reward_info = {
            "reward_total": total_reward,
            "reward_dist": r_dist * w_dist,
            "reward_ctrl": r_ctrl * w_ctrl,
            "reward_smooth": r_smooth * w_smooth, # 모니터링용 데이터 추가
            "reward_contact": r_contact * w_contact,
            "reward_bonus": r_bonus,
            "is_success": distance < threshold
        }
        
        return total_reward, reward_info