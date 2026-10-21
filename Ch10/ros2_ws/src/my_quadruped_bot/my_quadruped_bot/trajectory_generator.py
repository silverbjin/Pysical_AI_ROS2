#!/usr/bin/env python3
import numpy as np

class TrajectoryGenerator:
    """
    4족 보행 로봇의 발끝(End-Effector) 궤적을 생성하는 클래스.
    Cycloid 기반의 스윙 궤적과 안정적인 Raibert Heuristic 기반 대칭 스탠스 궤적을 제공한다.
    """
    # [수정] 생성자에 stance_depth 파라미터 추가 및 기본값(-0.30m) 지정
    def __init__(self, step_height: float = 0.05, stance_depth: float = -0.30) -> None:
        """
        Args:
            step_height (float): 발을 들어 올릴 목표 클리어런스 높이 (m)
            stance_depth (float): 기준 기립 높이 (m, 일반적으로 음수값)
        """
        self.step_height: float = step_height 
        self.stance_depth: float = stance_depth # [추가] 클래스 내부에서 전역 관리할 기립 깊이
        
        # [추가] 로봇 몸체 중심(Body Frame) 기준 각 다리의 기본 기립 원점 좌표 (X, Y, Z)
        # 로봇 제원에 맞게 간격(배치)을 설정합니다. (Z는 stance_depth 사용)
        self.nominal_positions = {
            'FR': np.array([ 0.12, -0.05, self.stance_depth]),
            'FL': np.array([ 0.12,  0.05, self.stance_depth]),
            'RR': np.array([-0.12, -0.05, self.stance_depth]),
            'RL': np.array([-0.12,  0.05, self.stance_depth])
        }

    def generate_swing(self, start_pos: np.ndarray, end_pos: np.ndarray, swing_phase: float) -> np.ndarray:
        """
        스윙(유각기) 단계의 3차원 발끝 목표 좌표를 계산한다.
        """
        s = np.clip(swing_phase, 0.0, 1.0)

        # 1. 수평 이동 (X, Y축): 사이클로이드 보간
        s_prime = s - (1.0 / (2.0 * np.pi)) * np.sin(2.0 * np.pi * s)
        current_x = (1.0 - s_prime) * start_pos[0] + s_prime * end_pos[0]
        current_y = (1.0 - s_prime) * start_pos[1] + s_prime * end_pos[1]

        # 2. 수직 이동 (Z축): 지면 높이 보간 및 가감속 충격 완화 곡선 적용
        base_z = (1.0 - s_prime) * start_pos[2] + s_prime * end_pos[2]
        
        if s < 0.5:
            z_phase = 2.0 * s
            z_prime = z_phase - (1.0 / (2.0 * np.pi)) * np.sin(2.0 * np.pi * z_phase)
            height_offset = self.step_height * z_prime
        else:
            z_phase = 2.0 * (1.0 - s)
            z_prime = z_phase - (1.0 / (2.0 * np.pi)) * np.sin(2.0 * np.pi * z_phase)
            height_offset = self.step_height * z_prime

        current_z = base_z + height_offset
        return np.array([current_x, current_y, current_z])

    def generate_stance(self, nominal_pos: np.ndarray, velocity_cmd: np.ndarray, 
                         stance_phase: float, T_cycle: float, duty_factor: float) -> np.ndarray:
        """
        스탠스(입각기) 단계의 발끝 좌표를 계산한다.
        - X, Y축은 nominal_pos 기준으로 스트로크를 계산하고, Z축은 self.stance_depth로 강제 고정한다.
        """
        s = np.clip(stance_phase, 0.0, 1.0)
        
        # 전체 스탠스 시간 및 총 스트로크 거리 연산
        T_stance = T_cycle * duty_factor
        stroke = velocity_cmd * T_stance
        
        # 수평 좌표 선형 트래킹
        next_pos = nominal_pos + (0.5 - s) * stroke
        
        # [수정] 외부 유입 nominal_pos[2] 대신 클래스 멤버 변수인 self.stance_depth를 명시적으로 적용
        next_pos[2] = self.stance_depth
        
        return next_pos
    
    def calculate_foothold(self, nominal_hip_pos: np.ndarray, velocity_cmd: np.ndarray, 
                            stance_duration: float, current_velocity: np.ndarray = None, 
                            k_v: float = 0.0) -> np.ndarray:
        """
        [Raibert Heuristic] 현재 속도 명령과 물리 주기를 바탕으로 목표 착지점(Foothold)을 계산한다.
        """
        # 1. 피드포워드 중립 위치 오프셋 연산
        feedforward_offset = velocity_cmd * stance_duration * 0.5
        
        # 2. 속도 오차 비례 피드백 오프셋 연산
        feedback_offset = np.zeros(3)
        if current_velocity is not None and k_v > 0.0:
            velocity_error = current_velocity - velocity_cmd
            feedback_offset = k_v * velocity_error
            feedback_offset[2] = 0.0
            
        # 3. 최종 목표 착지점 매핑
        target_x = nominal_hip_pos[0] + feedforward_offset[0] + feedback_offset[0]
        target_y = nominal_hip_pos[1] + feedforward_offset[1] + feedback_offset[1]
        
        # [수정] 시스템 제약조건 기립 높이를 self.stance_depth로 엄격하게 고정
        target_z = self.stance_depth
        
        return np.array([target_x, target_y, target_z])
    
    # =========================================================================
    # 🌟 [핵심 추가] quadruped_controller.py와 맞물리는 고수준 통합 인터페이스
    # =========================================================================
    def generate(self, leg_id: str, phase: float, is_swing: bool, velocity: np.ndarray) -> np.ndarray:
        """
        컨트롤러 노드에서 호출하는 메인 오케스트레이터 함수.
        다리의 상태(is_swing)에 따라 적절한 궤적 생성 로직을 분기 실행한다.
        """
        # 하드코딩 환경 변수 연동 (Trot 보행 표준 주기설정 정보 매핑)
        T_cycle = 0.5
        duty_factor = 0.5
        T_stance = T_cycle * duty_factor
        
        # 현재 제어 대상 다리의 기준 원점 로드
        nominal_pos = self.nominal_positions[leg_id].copy()
        
        if is_swing:
            # [유각기] 스탠스가 끝나는 지점(-stroke/2)에서 시작하여 Raibert 착지점 지점으로 이동
            stroke = velocity * T_stance
            start_pos = nominal_pos - 0.5 * stroke
            end_pos = self.calculate_foothold(nominal_pos, velocity, T_stance)
            
            # 수직 사이클로이드가 포함된 스윙 좌표 반환
            return self.generate_swing(start_pos, end_pos, phase)
        else:
            # [입각기] 절대 중심 트래킹 기법 기반 스탠스 좌표 반환
            return self.generate_stance(nominal_pos, velocity, phase, T_cycle, duty_factor)