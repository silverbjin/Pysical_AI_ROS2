from setuptools import setup
package_name='ch15_mission'
setup(name=package_name,version='0.1.0',packages=[package_name],data_files=[('share/ament_index/resource_index/packages',['resource/'+package_name]),('share/'+package_name,['package.xml']),('share/'+package_name+'/launch',['launch/mission.launch.py'])],install_requires=['setuptools'],zip_safe=True,maintainer='Ch15 maintainers',maintainer_email='maintainer@example.invalid',description='Educational mock contracts',license='TODO',entry_points={'console_scripts':['mission_executor = ch15_mission.mission_executor:main']})
