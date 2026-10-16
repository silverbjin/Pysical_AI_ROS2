#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
# [필수 추가] MoveIt 2 콜리전 객체 및 모양 메시지 임포트
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

class CollisionObjectManager(Node):
    def __init__(self):
        super().__init__('collision_object_manager')

        # 1. Planning Scene 전용 퍼블리셔 정의
        # MoveIt은 이 토픽을 감시하다가 새로운 객체가 들어오면 3D 월드에 등록합니다.
        self.scene_pub = self.create_publisher(PlanningScene, '/planning_scene', 10)

        # 타이머를 두어 1초마다 물체 위치를 갱신 (비전 데이터 반영)
        self.timer = self.create_timer(1.0, self.publish_coke_can)

        self.get_logger().info("MoveIt 2 Collision Object Manager Initialized.")

    def publish_coke_can(self):
        """코카콜라 캔 모양의 원기둥을 MoveIt Planning Scene에 발행"""
        coke_can = CollisionObject()
        
        # [핵심] 어느 프레임 기준으로 이 물체를 띄울 것인가?
        # 이전 노드에서 발행한 dynamic TF인 'target_object'를 그대로 사용!
        # 물체가 움직여도 TF가 움직이면 형상도 같이 움직입니다.
        coke_can.header.frame_id = "target_object"
        coke_can.id = "coke_can_0" # MoveIt 내 고유 이름
        coke_can.operation = CollisionObject.ADD # 생성/갱신 명령

        # 2. 물체의 모양(Geometry) 정의 - 코카콜라 캔 (원기둥)
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.CYLINDER
        # 코카콜라 캔 표준 규격 (높이 12cm, 지름 6.6cm) -> 단위: 미터
        primitive.dimensions = [0.12, 0.033] # [Height, Radius]

        coke_can.primitives.append(primitive)

        # 3. 물체의 자세(Pose) 정의
        coke_can_pose = Pose()
        # 원기둥의 중심점 위치 설정. 
        # TF 좌표축 바로 위에 캔 바닥이 오게 하려면 높이의 절반만큼 위로 올림.
        coke_can_pose.position.z = 0.06 
        coke_can_pose.orientation.w = 1.0 # 회전 없음

        coke_can.primitive_poses.append(coke_can_pose)

        # 4. 최종 Planning Scene 메시지로 포장하여 발행
        scene = PlanningScene()
        scene.world.collision_objects.append(coke_can)
        scene.is_diff = True # 부분 업데이트 선언 (매우 중요!)

        self.scene_pub.publish(scene)
        self.get_logger().info(f"Published Coke Can Model attached to [target_object] frame.")

def main(args=None):
    rclpy.init(args=args)
    node = CollisionObjectManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()