from setuptools import setup
setup(name='ch14_performance_monitor',version='0.1.0',packages=['ch14_performance_monitor'],
      data_files=[('share/ament_index/resource_index/packages',['resource/ch14_performance_monitor']),('share/ch14_performance_monitor',['package.xml'])],
      install_requires=['setuptools'],zip_safe=False,
      entry_points={'console_scripts':['monitor_node=ch14_performance_monitor.monitor_node:main']})
