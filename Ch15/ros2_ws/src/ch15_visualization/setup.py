from setuptools import setup
from glob import glob
p='ch15_visualization'
setup(name=p,version='0.1.0',packages=[p],
      data_files=[('share/ament_index/resource_index/packages',['resource/'+p]),
                  ('share/'+p,['package.xml']),
                  ('share/'+p+'/launch',glob('launch/*.xml')),
                  ('share/'+p+'/rviz',glob('rviz/*.rviz'))],
      install_requires=['setuptools'],zip_safe=True,
      description='Read-only mission visualization',license='TODO',
      entry_points={'console_scripts':['mission_marker_node = ch15_visualization.mission_marker_node:main']})
