from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'my_quadruped_bot'

# =========================================================================
# [실무 팁] 하위 디렉토리 구조를 그대로 유지하며 파일을 수집하는 헬퍼 함수
# =========================================================================
def walk_and_collect(source_dir, target_base):
    data_files = []
    for root, dirs, files in os.walk(source_dir):
        if files:
            # 소스 디렉토리 기준 상대 경로 계산 (예: 'urdf/common' -> 'common')
            rel_path = os.path.relpath(root, source_dir)
            if rel_path == '.':
                target_dir = target_base
            else:
                target_dir = os.path.join(target_base, rel_path)
            
            # 해당 폴더 내의 모든 파일 경로 매핑
            file_paths = [os.path.join(root, f) for f in files]
            data_files.append((target_dir, file_paths))
    return data_files

# 기본 데이터 파일 정의
base_data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),
    (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
    (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),    
    (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),        
]

# urdf 폴더 하위의 모든 구조를 동적으로 수집하여 결합
dynamic_urdf_files = walk_and_collect('urdf', os.path.join('share', package_name, 'urdf'))
final_data_files = base_data_files + dynamic_urdf_files

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=final_data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jinho',
    maintainer_email='jinho@todo.todo',
    description='Physical AI Quadruped Robot Package',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'stand_up = my_quadruped_bot.stand_up:main',
            'single_leg_mover = my_quadruped_bot.single_leg_mover:main',
            'trot_gait_preview = my_quadruped_bot.trot_gait_preview:main',
            'quadruped_controller = my_quadruped_bot.quadruped_controller:main',
            'gait_planner = my_quadruped_bot.gait_planner:main',
            'trot_controllerFSM = my_quadruped_bot.trot_controllerFSM:main',
            'quadruped_controller_ros2 = my_quadruped_bot.quadruped_controller_ros2:main',
            # Ch11
            'imu_processor = my_quadruped_bot.imu_processor:main',      
            'lidar_safety = my_quadruped_bot.lidar_safety:main',      
            'sim_odometry = my_quadruped_bot.sim_odometry:main',
            'command_odometry_demo = my_quadruped_bot.command_odometry_demo:main',
        ],
    },
)
