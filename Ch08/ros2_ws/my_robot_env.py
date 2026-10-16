import gymnasium as gym
from gymnasium import spaces
import numpy as np
import mujoco
import os

class MuJoCoArmEnv(gym.Env):
    """
    MuJoCo 3.3.0 시뮬레이터와 연동되는 3관절 로봇 팔 강화학습 환경
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(self, model_path="src/my_robot_description/assets/simple_arm_3dof.xml", render_mode=None):
        super(MuJoCoArmEnv, self).__init__()
        
        # 1. MuJoCo 모델 및 데이터 로드
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        
        self.render_mode = render_mode
        self.viewer = None # MuJoCo 3.x Passive Viewer 객체

        # [최적화] 매 step마다 ID를 찾지 않도록, End-Effector의 ID를 미리 캐싱해 둡니다.
        self.ee_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "link_ee")

        # 2. 행동 공간 (Action Space): 3개 관절의 토크 제어 (-1.0 ~ 1.0)
        # n_actions = 3, n_observations = 12 (상대벡터 포함) 설정을 그대로 사용할 수 있습니다!
        n_actions = 3
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(n_actions,), dtype=np.float32
        )
        
        # 3. 관측 공간 (Observation Space): 총 12차원
        # [관절각도(3), 관절속도(3), 목표좌표(3), 목표와의 상대벡터(3)]
        n_observations = 12
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_observations,), dtype=np.float32
        )
        
        # 목표 지점 초기화
        self.target_pos = np.array([0.5, 0.0, 0.5])

    def _get_obs(self):
        """
        현재 물리 시뮬레이터의 상태를 강화학습 Agent가 인식할 수 있는 1D 벡터로 변환합니다.
        """
        qpos = self.data.qpos[:3].astype(np.float32)
        qvel = self.data.qvel[:3].astype(np.float32)
        target = self.target_pos.astype(np.float32)
        
        # End-Effector의 현재 글로벌 좌표 획득 (Forward Kinematics 결과)
        ee_pos = self.data.xpos[self.ee_id].astype(np.float32)
        
        # 상대 벡터 계산 (에이전트가 목표 방향을 더 직관적으로 알게 됨)
        rel_vec = target - ee_pos
        
        # 12차원 배열로 병합
        return np.concatenate([qpos, qvel, target, rel_vec])

    def reset(self, seed=None, options=None):
        """
        에피소드 초기화 및 도메인 랜덤화(Domain Randomization) 수행
        """
        super().reset(seed=seed)
        
        # 물리 엔진 상태 초기화
        mujoco.mj_resetData(self.model, self.data)
        
        # 작업 영역(Workspace) 내에서 목표물을 무작위로 생성 (강건한 학습 유도)
        self.target_pos = np.random.uniform(
            low=[0.3, -0.2, 0.3], high=[0.7, 0.2, 0.6]
        )
        
        # 초기화된 값으로 물리 연산을 1회 수행하여 위치 에너지 및 센서 동기화
        mujoco.mj_forward(self.model, self.data)
        
        return self._get_obs(), {}
    
    def step(self, action):
        """
        Agent의 제어 입력(Torque)을 받아 물리 엔진을 한 스텝 진행시킵니다.
        """
        # 1. Action 적용 (정규화된 값을 실제 토크 값으로 스케일링)
        motor_scaling = 50.0
        self.data.ctrl[:] = action * motor_scaling
        
        # 2. 물리 시뮬레이션 (Frame Skip 적용)
        # 강화학습은 초당 50~100번의 의사결정이면 충분하지만, 물리 엔진은 초당 500번 이상의 계산이 필요함.
        for _ in range(10):
            mujoco.mj_step(self.model, self.data)
            
        # 3. 상태 관측
        observation = self._get_obs()
        ee_pos = self.data.xpos[self.ee_id]
        
        # 4. 보상 설계 (Reward Shaping)
        distance = np.linalg.norm(ee_pos - self.target_pos)
        reward = -distance # 거리가 멀수록 페널티
        
        # 5. 종료 조건
        terminated = False
        if distance < 0.05: # 목표 반경 5cm 이내 도달
            reward += 10.0  # 성공 보너스 부여
            terminated = True
            
        truncated = False
        info = {"distance": distance}
        
        return observation, reward, terminated, truncated, info

    def render(self):
        """
        MuJoCo 3.x의 최신 뷰어(Passive Viewer)를 이용한 화면 출력
        """
        if self.render_mode == "human":
            if self.viewer is None:
                from mujoco import viewer
                # 시뮬레이션 루프를 멈추지 않는 passive viewer 실행
                self.viewer = viewer.launch_passive(self.model, self.data)
            
            # 물리 엔진의 변화를 뷰어와 동기화
            self.viewer.sync()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()