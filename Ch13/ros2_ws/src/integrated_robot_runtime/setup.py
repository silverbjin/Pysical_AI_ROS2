from glob import glob
from setuptools import setup

setup(
    name='integrated_robot_runtime', version='0.3.0',
    packages=['integrated_robot_runtime'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/integrated_robot_runtime']),
        ('share/integrated_robot_runtime', ['package.xml']),
        ('share/integrated_robot_runtime/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    tests_require=['pytest'],
    maintainer='Jinho', maintainer_email='jinho@todo.todo',
    description='Section 13.3 runtime', license='Apache-2.0',
    entry_points={'console_scripts': [
        'locomotion_node = integrated_robot_runtime.locomotion:main',
        'manipulation_node = integrated_robot_runtime.manipulation:main',
        'state_manager = integrated_robot_runtime.state_manager:main',
        'vision_processor = integrated_robot_runtime.vision:main',
        'mission_commander = integrated_robot_runtime.mission:main',
        'tracking_requester = integrated_robot_runtime.tracking_requester:main',
    ]},
)
