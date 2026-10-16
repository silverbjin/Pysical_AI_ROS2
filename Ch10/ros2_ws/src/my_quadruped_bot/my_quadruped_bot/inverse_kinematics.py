#!/usr/bin/env python3
import numpy as np

class InverseKinematics:
    """
    4족 보행 로봇 다리의 해석적 역운동학(Analytical IK) 솔버
    - 기립 상태(0도)가 수직 아래를 향하는 URDF 표준 모델링 기준
    """
    def __init__(self, leg_config=None):
        # 로봇의 기구학적 제원 (m 단위)
        self.l1 = 0.05  # Hip offset length (y축 이격 거리)
        self.l2 = 0.20  # Thigh length (허벅지)
        self.l3 = 0.20  # Calf length (종아리)
        
        self.epsilon = 1e-6

    def solve(self, x: float, y: float, z: float, is_right_leg: bool = False):
        """
        단일 다리에 대한 역운동학 각도 도출
        Args:
            x, y, z (float): Hip Frame 기준 3차원 목표 좌표
            is_right_leg (bool): 우측 다리 여부 (대칭성 보정용)
        Returns:
            np.ndarray: [q1, q2, q3] 관절 각도 (rad), 도달 불가 시 None
        """
        # [대칭 보정] 우측 다리는 Y축 좌표를 반전시켜 좌측 다리와 동일한 평면 문제로 치환
        modified_y = -y if is_right_leg else y

        # --- Step 1: Hip Roll (q1) ---
        yz_dist = np.sqrt(modified_y**2 + z**2)
        
        # 도달 불가능 예외 처리 (목표점이 힙 오프셋 반경보다 안쪽에 있는 경우)
        if yz_dist < self.l1:
            return None

        # 아크사인 도메인 에러 방지를 위한 클램핑
        ratio = np.clip(self.l1 / yz_dist, -1.0, 1.0)
        
        # Z축 아래 방향이 음수이므로 -z가 양수 거리가 됨
        alpha = np.arctan2(modified_y, -z)
        beta = np.arcsin(ratio)
        
        q1 = alpha - beta
        
        # [대칭 보정 복구] 우측 다리인 경우 도출된 Roll 각도의 부호를 반전
        if is_right_leg:
            q1 = -q1 

        # --- Step 2: 3D to 2D Projection ---
        # 힙 관절 축이 회전한 후, 허벅지/종아리가 위치할 2D 평면상의 투영 깊이(음수)
        z_prime = -np.sqrt(max(0.0, yz_dist**2 - self.l1**2))
        
        # --- Step 3: Thigh (q2) & Calf (q3) ---
        dist_sq = x**2 + z_prime**2
        max_reach = self.l2 + self.l3
        
        # 특이점(Singularity) 및 도달 불가능 영역 클램핑
        if dist_sq > max_reach**2:
            scale = max_reach / np.sqrt(dist_sq)
            x *= scale
            z_prime *= scale
            dist_sq = max_reach**2
        
        # [수학적 수정] 무릎 관절 각도는 다리가 일자로 펴졌을 때 0도여야 함
        # cos(q3) = (D^2 - l2^2 - l3^2) / (2 * l2 * l3)
        numerator = dist_sq - self.l2**2 - self.l3**2
        denominator = 2 * self.l2 * self.l3
        cos_q3 = np.clip(numerator / denominator, -1.0, 1.0)
        
        # 4족 보행의 무릎 형상 (Dog-leg, Elbow Backward)
        # 종아리가 뒤로 꺾이려면 양수(Positive) 각도를 취함
        q3 = np.arccos(cos_q3)
        
        # [수학적 수정] 0도가 수직 아래를 향하도록 축 정렬
        # phi: -Z축(아래) 기준으로 목표점까지의 각도 (앞으로 뻗으면 양수)
        phi = np.arctan2(x, -z_prime)
        
        # psi: 가상의 직선(힙~발끝)과 허벅지 링크(l2) 사이의 내부 편차 각도
        psi = np.arctan2(self.l3 * np.sin(q3), self.l2 + self.l3 * np.cos(q3))
        
        # 최종 허벅지 각도 도출
        q2 = phi - psi
        
        return np.array([q1, q2, q3])
    