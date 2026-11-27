from setuptools import setup
from glob import glob
p='ch15_simulation'
setup(name=p,version='0.1.0',packages=[p],data_files=[('share/ament_index/resource_index/packages',['resource/'+p]),('share/'+p,['package.xml']),('share/'+p+'/worlds',glob('worlds/*.sdf')),('share/'+p+'/models/red_cube',glob('models/red_cube/*')),('share/'+p+'/models',glob('models/*.xml')+glob('models/*.urdf'))],install_requires=['setuptools'],zip_safe=True,maintainer='Ch15 maintainers',maintainer_email='maintainer@example.invalid',description='RGB-D educational lab',license='TODO',entry_points={'console_scripts':['cube_detector = ch15_simulation.cube_detector:main']})
