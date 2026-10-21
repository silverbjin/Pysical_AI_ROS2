import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'vision_basics'  # 독자의 실습 환경에 따라 패키지명이 다를 수 있음을 본문에 명시해야 합니다.

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # =========================================================================
        # 실무 가이드: 외부 리소스 폴더의 파일들을 빌드 시 share 디렉토리로 복사
        # 디렉토리가 복사되어 에러가 나는 것을 방지하기 위해 
        # 특정 확장자(*.urdf, *.xacro, *.yaml 등)만 명시적으로 타겟팅합니다.
        # =========================================================================
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf') + glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),    
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),        
        (os.path.join('share', package_name, 'models'), glob('models/*')), # ⬅️ 추가 확인
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jinho',
    maintainer_email='silverbjin@gmail.com',
    description='Physical AI Ch07 vision and manipulation labs',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # 추후 텔레오퍼레이션이나 제어 노드 작성 시 여기에 등록합니다.
            'simple_arm_teleop = vision_basics.simple_arm_teleop:main',  # 텔레오퍼레이션 노드 추가
            'joint_control_cli = vision_basics.joint_control_cli:main',  # 제어 노드 추가
            
            'joint_splitter = vision_basics.joint_splitter:main',
            'simple_image_subscriber = vision_basics.simple_image_subscriber:main',
            'vision_processor = vision_basics.vision_processor:main',
            'object_detector = vision_basics.object_detector:main',
            'gripper_controller = vision_basics.gripper_controller:main',
            'mission_controller = vision_basics.mission_controller:main',
        ],
    },
)
