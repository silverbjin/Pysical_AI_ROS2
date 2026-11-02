from setuptools import setup
from glob import glob
from pathlib import Path
package='ch13_navigation_reuse'
ch13=Path(__file__).resolve().parents[3]
setup(name=package,version='0.1.0',packages=[package],data_files=[('share/ament_index/resource_index/packages',['resource/'+package]),('share/'+package,['package.xml']),('share/'+package+'/config',glob('config/*')),('share/'+package+'/launch',glob('launch/*')),('share/'+package+'/upstream_corrections',['../../../scripts/reuse_13_5/reproduce_upstream.py','../../../scripts/reuse_13_5/third_party/IIT_DLSLab_BSD-3-Clause.txt'])],install_requires=['setuptools'],zip_safe=False,maintainer='Ch13',maintainer_email='maintainer@example.invalid',description='Opt-in corrected Go2/Piper ROS2 boundary',license='BSD-3-Clause',entry_points={'console_scripts':['command_gateway = ch13_navigation_reuse.command_gateway:main','platform_adapter = ch13_navigation_reuse.platform_adapter:main']})
