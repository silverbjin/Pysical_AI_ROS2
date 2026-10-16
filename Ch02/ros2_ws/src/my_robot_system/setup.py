import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_robot_system'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # [추가] launch 디렉터리의 모든 .py 파일을 share/패키지명/launch로 설치
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jinho',
    maintainer_email='jinho@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joint_sensor = my_robot_system.joint_sensor_node:main',
            'turtle_cmd_pub = my_robot_system.turtle_cmd_publisher:main', # 추가
            'turtle_pose_sub = my_robot_system.turtle_pose_subscriber:main', # 추가
            'turtle_spawn_client = my_robot_system.turtle_spawn_client:main', # 추가
            'add_two_ints_server = my_robot_system.add_two_ints_server:main', # 추가
            'hw_status_publisher = my_robot_system.hw_status_publisher:main', # 추가
            'count_until_server = my_robot_system.count_until_server:main', # 추가
            'count_until_client = my_robot_system.count_until_client:main', # 추가
            'turtle_patrol = my_robot_system.turtle_patrol:main', # 추가
            'qos_test_node = my_robot_system.qos_test_node:main', # 추가    
        ],
    },
)
