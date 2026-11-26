from setuptools import setup, find_packages
setup(name='ch14_ai_perception', version='0.1.0', packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages',['resource/ch14_ai_perception']),
                  ('share/ch14_ai_perception',['package.xml','LICENSE.ch13','REUSE_NOTICE.md']),
                  ('share/ch14_ai_perception/launch',['launch/perception.launch.py','launch/robot_ai_system.launch.py']),
                  ('share/ch14_ai_perception/config',['config/params_replay.yaml','config/params_sim.yaml'])],
      install_requires=['setuptools'],zip_safe=False,
      entry_points={'console_scripts':['detector_node=ch14_ai_perception.detector_node:main']})
