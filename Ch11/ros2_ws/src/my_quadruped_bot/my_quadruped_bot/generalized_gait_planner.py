import numpy as np

class GaitConfig:
    """ 보행 패턴의 파라미터를 저장하는 데이터 클래스 """
    def __init__(self, name, duty_factor, offsets, frequency):
        self.name = name
        self.duty_factor = duty_factor
        # offsets 순서: [FL, FR, RL, RR]
        self.offsets = np.array(offsets)
        self.frequency = frequency # Hz

# 미리 정의된 보행 패턴 라이브러리
GAIT_LIBRARY = {
    'trot': GaitConfig('trot', 0.5, [0.0, 0.5, 0.5, 0.0], 2.0),
    'pace': GaitConfig('pace', 0.5, [0.0, 0.5, 0.0, 0.5], 2.0),
    'bound': GaitConfig('bound', 0.5, [0.0, 0.0, 0.5, 0.5], 2.5),
    'crawl': GaitConfig('crawl', 0.75, [0.0, 0.5, 0.25, 0.75], 1.0)
}

class GeneralizedGaitPlanner:
    def __init__(self, initial_gait='trot'):
        self.current_gait = GAIT_LIBRARY[initial_gait]
        self.next_gait = None  
        self.current_time = 0.0
        self.cycle_completed = False  # [추가] 주기 완료 여부를 저장할 플래그
        
    def set_gait(self, gait_name):
        """ 실시간으로 보행 패턴 전환을 예약한다 """
        if gait_name in GAIT_LIBRARY:
            self.next_gait = GAIT_LIBRARY[gait_name]
        else:
            print(f"Warning: Unknown gait {gait_name}")
 
    def update(self, dt):
        """ 시간을 누적하고 주기가 끝나는 시점에 안전하게 보행을 전이한다 """
        self.current_time += dt
        self.cycle_completed = False  # 매 스텝마다 플래그 초기화
        
        # 사이클이 초기화되는 시점에 변경 적용
        T_current = 1.0 / self.current_gait.frequency
        if self.current_time >= T_current:
            self.current_time -= T_current 
            self.cycle_completed = True  # 한 주기가 성공적으로 완료됨을 기록
            
            # 대기 중인 다음 보행 패턴이 있다면 이때 스위칭
            if self.next_gait is not None:
                self.current_gait = self.next_gait
                self.next_gait = None

    def is_cycle_completed(self):
        """ [추가] FSM 노드에서 현재 보행 주기가 완료되었는지 확인할 수 있는 인터페이스 """
        return self.cycle_completed

    def get_leg_states(self):
        """ 
        현재 보행 설정과 시간에 따른 각 다리의 정규화된 위상(0~1) 및 스윙 여부 반환
        """
        T_cycle = 1.0 / self.current_gait.frequency
        phi_global = (self.current_time % T_cycle) / T_cycle
        
        leg_names = ['FL', 'FR', 'RL', 'RR']
        leg_states = {}
        
        duty_factor = self.current_gait.duty_factor
        
        for i, name in enumerate(leg_names):
            phi_i = (phi_global + self.current_gait.offsets[i]) % 1.0
            
            if phi_i < duty_factor:
                is_swing = False
                normalized_phase = phi_i / duty_factor
            else:
                is_swing = True
                normalized_phase = (phi_i - duty_factor) / (1.0 - duty_factor)
                
            leg_states[name] = (normalized_phase, is_swing)
            
        return leg_states