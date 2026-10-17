from glob import glob
from setuptools import setup,find_packages

setup(name='quadruped_rl_ros',version='0.8.0',packages=find_packages(),
    data_files=[('share/ament_index/resource_index/packages',['resource/quadruped_rl_ros']),
        ('share/quadruped_rl_ros',['package.xml']),
        ('share/quadruped_rl_ros/launch',glob('launch/*.launch.py'))],
    install_requires=['setuptools'],entry_points={'console_scripts':[
        'rl_controller = quadruped_rl_ros.rl_controller:main',
        'mujoco_bridge = quadruped_rl_ros.mujoco_bridge:main']})
