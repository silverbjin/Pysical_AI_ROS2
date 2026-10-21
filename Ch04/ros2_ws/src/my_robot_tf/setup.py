import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_robot_tf'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # for launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
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
            'static_tf_broadcaster = my_robot_tf.static_tf_broadcaster:main',
            'dynamic_tf_broadcaster = my_robot_tf.dynamic_tf_broadcaster:main', # 추가
            'tf_listener = my_robot_tf.tf_listener:main', # 추가
            'joint_position_cli = my_robot_tf.joint_position_cli:main',
        ],
    },
)
