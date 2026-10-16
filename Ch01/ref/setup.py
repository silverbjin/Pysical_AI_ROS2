from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'my_first_package'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # 향후 런칭 파일을 위해 추가적인 경로 설정 가능
        # (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='YourName',
    maintainer_email='your_email@domain.com',
    description='ROS 2 Jazzy 시작하기: 기초 노드 및 의존성 관리 실습',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # 터미널에서 실행할 명령어 = 패키지명.파일명:함수명
            'simple_node = my_first_package.simple_node:main',
            'cmd_publisher = my_first_package.cmd_publisher_node:main',
        ],
    },
)