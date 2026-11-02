from glob import glob
from setuptools import setup
setup(name='ch13_control',version='0.1.0',packages=['ch13_control'],data_files=[('share/ament_index/resource_index/packages',['resource/ch13_control']),('share/ch13_control',['package.xml']),('share/ch13_control/launch',glob('launch/*.launch.py'))],install_requires=['setuptools'],tests_require=['pytest'],entry_points={'console_scripts':[f'{n} = ch13_control.{n}:main' for n in ('state_monitor','command_arbiter_node','hold_controller','mujoco_bridge','gazebo_router','rl_leg_controller')]})
