from setuptools import setup
p='ch13_system_validation'
setup(name=p,version='0.1.0',packages=[p],data_files=[
 ('share/ament_index/resource_index/packages',['resource/'+p]),('share/'+p,['package.xml'])],
 install_requires=['setuptools'],zip_safe=False,maintainer='Ch13',
 maintainer_email='maintainer@example.invalid',description='Chapter13 integrated validation',license='BSD-3-Clause')
