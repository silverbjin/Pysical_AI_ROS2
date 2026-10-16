import math
import numpy as np

# 로봇 팔 링크 길이 정의 (단위: m) 
L1 = 0.5
L2 = 0.5

def forward_kinematics(theta1, theta2):
    """
    정운동학: 각도(theta)를 주면 위치(x, y)를 반환
    """
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    y = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)
    return np.array([x, y])

def compute_jacobian(theta1, theta2):
    """
    야코비안 행렬 계산: 관절 속도와 말단 속도의 관계를 나타내는 행렬
    미분 값을 통해 현재 위치에서 조금 움직였을 때 x, y가 얼마나 변하는지 계산
    """
    j11 = -L1 * math.sin(theta1) - L2 * math.sin(theta1 + theta2)
    j12 = -L2 * math.sin(theta1 + theta2)
    j21 =  L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    j22 =  L2 * math.cos(theta1 + theta2)
    
    return np.array([[j11, j12], [j21, j22]])

def inverse_kinematics_numerical(target_x, target_y, init_theta1=0.1, init_theta2=0.1):
    """
    수치해석적 역운동학 (Newton-Raphson Method)
    : 목표 위치와 현재 위치의 오차를 줄여가는 반복(Iteration) 과정
    """
    # 초기 관절 각도 설정
    theta = np.array([init_theta1, init_theta2])
    
    # 반복 학습 설정
    learning_rate = 0.1
    tolerance = 0.001 # 허용 오차 (1mm)
    max_iter = 100    # 최대 반복 횟수

    print(f"--- IK Calculation Start: Target({target_x}, {target_y}) ---")

    for i in range(max_iter):
        # 1. 현재 각도에서의 위치 계산 (Forward Kinematics)
        current_pos = forward_kinematics(theta[0], theta[1])
        
        # 2. 오차 계산 (목표 위치 - 현재 위치)
        error = np.array([target_x, target_y]) - current_pos
        
        # 오차가 허용 범위 내라면 종료 (성공)
        if np.linalg.norm(error) < tolerance:
            print(f"Converged at iter {i}: Theta1={math.degrees(theta[0]):.2f}°, Theta2={math.degrees(theta[1]):.2f}°")
            return theta

        # 3. 야코비안 행렬 계산 및 역행렬 구하기 (Pseudo-Inverse 사용 권장)
        J = compute_jacobian(theta[0], theta[1])
        
        try:
            # 특이점 근처에서는 역행렬 계산이 불안정할 수 있음 (Damped Least Squares 등 실무적용 필요)
            J_inv = np.linalg.pinv(J) 
        except np.linalg.LinAlgError:
            print("Singularity encountered!")
            return None

        # 4. 각도 업데이트: 현재 각도 + (역야코비안 * 오차)
        delta_theta = J_inv @ error
        theta = theta + learning_rate * delta_theta

    print("Failed to converge within max iterations.")
    return None

# 실행 예시
if __name__ == "__main__":
    # (0.7, 0.0) 위치로 이동하기 위한 각도 찾기
    result_theta = inverse_kinematics_numerical(0.7, 0.0)
