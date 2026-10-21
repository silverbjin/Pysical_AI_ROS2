from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'manipulation_basics'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch 파일 포함
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # Config 파일 포함
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        # [치명적 오류 수정] urdf 폴더 내의 모든 파일(*.xacro, *.urdf, 복합 확장자 포함)을 
        # 누락 없이 install 디렉토리로 안전하게 복사하도록 수정
        # (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf') + glob('urdf/*.xacro')),
        # RViz 설정 파일 포함 (폴더째로 복사)
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jinho',
    maintainer_email='silverbjin@gmail.com',
    description='Basic manipulation control examples',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # 추후 작성할 노드 등록 예정
            'simple_controller = manipulation_basics.simple_joint_controller:main',
            'joint_listener = manipulation_basics.joint_state_listener:main',   # 5.4. 조인트 상태 트래킹            
            'wave_hello = manipulation_basics.wave_hello_node:main', # 5.6. Hello Robot 노드 등록

        ],
    },
)
