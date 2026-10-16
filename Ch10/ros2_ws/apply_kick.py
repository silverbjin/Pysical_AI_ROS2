#!/usr/bin/env python3
import subprocess
import json
import time
import sys

def apply_instant_force(world_name, model_name, link_name, force_vector, duration=0.1):
    """
    Gazebo Harmonic의 특정 링크에 순간적인 외란(Force)을 주입합니다.
    """
    # 1. Gazebo Topic 경로 설정
    # 주의: 가제보 버전에 따라 토픽명이 /forcetorque/wrenches 혹은 /wrench 일 수 있습니다.
    # 만약 에러가 나면 'gz topic -l' 명령어로 토픽 목록을 먼저 확인하세요.
    topic = f"/world/{world_name}/force_torque" 
    
    # 2. 인가할 힘 데이터 패킷 생성
    # EntityWrench 메시지 포맷에 맞춘 데이터 구성
    wrench_msg = {
        "entity": {
            "name": model_name,
            "type": 2,  # 2: MODEL 타입
            "chassis": {
                "name": link_name
            }
        },
        "wrench": {
            "force": {
                "x": force_vector[0],
                "y": force_vector[1],
                "z": force_vector[2]
            },
            "torque": {"x": 0.0, "y": 0.0, "z": 0.0}
        }
    }
    
    # 3. 제거(초기화)할 힘 데이터 패킷 (0N)
    zero_msg = json.loads(json.dumps(wrench_msg))
    zero_msg["wrench"]["force"] = {"x": 0.0, "y": 0.0, "z": 0.0}

    print(f"▶ [외란 주입] 월드: {world_name} | 모델: {model_name} | 링크: {link_name}")
    print(f"▶ [주입 세기] Force: {force_vector} N (지속시간: {duration}초)")

    try:
        # 힘 인가
        subprocess.run(["gz", "topic", "-t", topic, "-m", "gz.msgs.EntityWrench", "-p", json.dumps(wrench_msg)], check=True)
        
        # 지속 시간 대기
        time.sleep(duration)
        
        # 힘 제거
        subprocess.run(["gz", "topic", "-t", topic, "-m", "gz.msgs.EntityWrench", "-p", json.dumps(zero_msg)], check=True)
        print("✓ [외란 종료] 자세 복원력을 모니터링하세요.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 가제보 토픽 주입 실패: {e}", file=sys.stderr)
        print("💡 팁: 'gz topic -l' 명령어로 토픽 리스트를 확인하여 올바른 토픽 경로인지 체크하세요.")

if __name__ == "__main__":
    # --- 수정된 파라미터 ---
    WORLD = "my_empty_world"
    MODEL = "my_quadruped"
    LINK = "base_footprint"
    
    # [X, Y, Z] N 단위. Y축으로 50N을 가합니다.
    KICK_FORCE = [0.0, 50.0, 0.0] 
    DURATION = 0.1 
    
    apply_instant_force(WORLD, MODEL, LINK, KICK_FORCE, DURATION)