from setuptools import setup
package='ch13_manipulation_reuse'
setup(name=package,version='0.1.0',packages=[package],
      data_files=[('share/ament_index/resource_index/packages',['resource/'+package]),
                  ('share/'+package,['package.xml'])],install_requires=['setuptools'],
      zip_safe=False,maintainer='Ch13',maintainer_email='maintainer@example.invalid',
      description='Live Go2/Piper manipulation',license='BSD-3-Clause')
