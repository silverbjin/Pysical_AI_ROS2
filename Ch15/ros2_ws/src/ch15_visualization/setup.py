from setuptools import setup
p='ch15_visualization'
setup(name=p,version='0.1.0',packages=[p],data_files=[('share/ament_index/resource_index/packages',['resource/'+p]),('share/'+p,['package.xml'])],install_requires=['setuptools'],zip_safe=True,description='G05 installation scaffold',license='TODO')
