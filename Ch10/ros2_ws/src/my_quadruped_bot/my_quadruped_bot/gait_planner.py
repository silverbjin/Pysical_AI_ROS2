#!/usr/bin/env python3
import numpy as np
from typing import Dict, Tuple

class GaitPlanner:
    def __init__(self, gait_type: str = 'trot', cycle_time: float = 0.5):
        """
        4족 보행 로봇의 위상(Phase) 및 접촉 상태(Contact)를 관리하는 통합 스케줄러
        """
        self.T_cycle: float = cycle_time
        self.current_time: float = 0.0
        
        # 확장성을 위한 다리 순서 표준화 식별자
        self.leg_names = ['FL', 'FR', 'RL', 'RR']
        
        self.gait_type: str = ''
        self.duty_factor: float = 0.0
        self.phase_offsets: np.ndarray = np.zeros(4)
        
        self.set_gait_type(gait_type)
        
    def set_gait_type(self, gait_type: str) -> None:
        """
        보행 타입에 따라 Duty Factor와 다리별 Phase Offset을 동적으로 설정
        - 표준 인덱스 규칙 준수: [0: FL, 1: FR, 2: RL, 3: RR]
        """
        self.gait_type = gait_type
        
        if gait_type == 'trot':
            self.duty_factor = 0.5 
            self.phase_offsets = np.array([0.0, 0.5, 0.5, 0.0]) # FL-RR(동기), FR-RL(동기)
            
        elif gait_type == 'walk':
            self.duty_factor = 0.75 
            self.phase_offsets = np.array([0.0, 0.5, 0.75, 0.25])
            
        elif gait_type == 'pace':
            self.duty_factor = 0.5
            self.phase_offsets = np.array([0.0, 0.5, 0.0, 0.5]) # 좌측 그룹(FL-RL), 우측 그룹(FR-RR)
            
        else:
            raise ValueError(f"Unknown gait type: {gait_type}")

    def update(self, dt: float) -> None:
        """매 제어 주기(dt)마다 글로벌 물리 시간 업데이트 (내부 연산용)"""
        self.current_time += dt
        if self.current_time >= self.T_cycle:
            self.current_time -= self.T_cycle

    def get_leg_states(self) -> Dict[str, Tuple[float, bool]]:
        """
        [구조 통일] 현재 시간 기준 각 다리의 정규화된 위상(0.0~1.0) 및 유각기 여부 반환
        Returns:
            Dict[str, Tuple[float, bool]]: {'다리이름': (내부위상, 유각기여부)}
        """
        leg_states = {}
        
        # 글로벌 진행률 계산 (0.0 <= phi_global < 1.0)
        phi_global = self.current_time / self.T_cycle
        
        for i, name in enumerate(self.leg_names):
            # 각 다리별 오프셋 반영 및 래핑
            phi_i = (phi_global + self.phase_offsets[i]) % 1.0
            
            # 10.2절 표준 정의: 전반부(0 ~ duty_factor)는 Stance, 후반부는 Swing
            if phi_i < self.duty_factor:
                # 입각기 (Stance) -> 진행률을 0.0 ~ 1.0으로 정규화
                phase = phi_i / self.duty_factor
                is_swing = False
            else:
                # 유각기 (Swing) -> 진행률을 0.0 ~ 1.0으로 정규화
                phase = (phi_i - self.duty_factor) / (1.0 - self.duty_factor)
                is_swing = True
                
            leg_states[name] = (phase, is_swing)
            
        return leg_states

    def is_cycle_completed(self, epsilon: float = 0.04) -> bool:
        """
        [FSM 연동 핵심] 글로벌 보행 주기가 경계선(완료 시점)에 도달했는지 판단
        - 사용자가 속도 명령을 0으로 껐을 때, 네 발이 기립 자세(Nominal)로 정렬되는 타이밍 확보
        """
        phi_global = self.current_time / self.T_cycle
        # 주기가 막 끝나기 직전이거나 막 시작된 시점인지를 마진(epsilon)으로 판단
        return (phi_global < epsilon) or (phi_global > (1.0 - epsilon))
