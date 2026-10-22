from glob import glob
from setuptools import find_packages, setup

setup(
    name='integrated_robot_navigation', version='0.5.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/integrated_robot_navigation']),
        ('share/integrated_robot_navigation', ['package.xml']),
        ('share/integrated_robot_navigation/config', glob('config/*.yaml')),
        ('share/integrated_robot_navigation/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools', 'numpy', 'PyYAML', 'mujoco==3.3.7'], zip_safe=True,
    maintainer='Jinho', maintainer_email='jinho@todo.todo',
    description='Measured contact-driven crawl navigation for Ch13',
    license='Apache-2.0', tests_require=['pytest'],
    entry_points={'console_scripts': [
        'gazebo_contact_adapter = integrated_robot_navigation.gazebo_contacts:main',
    ]},
)
