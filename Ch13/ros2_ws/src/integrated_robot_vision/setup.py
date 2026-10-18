from setuptools import find_packages, setup

setup(
    name='integrated_robot_vision', version='0.4.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/integrated_robot_vision']),
        ('share/integrated_robot_vision', ['package.xml']),
    ],
    install_requires=['setuptools', 'numpy'], zip_safe=True,
    maintainer='Jinho', maintainer_email='jinho@todo.todo',
    description='Stamped RGB-D perception for Ch13', license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'native_pose_adapter = integrated_robot_vision.native_pose:main',
        'native_camera_info_adapter = integrated_robot_vision.camera_info_adapter:main',
    ]},
)
