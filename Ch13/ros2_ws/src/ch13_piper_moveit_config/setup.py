import os
from glob import glob
from setuptools import setup
package='ch13_piper_moveit_config'
generated=os.environ.get('CH13_REUSE_GENERATED','/home/jinho/ch13_reuse_13_6_build/model')
generated_files=[os.path.relpath(path,os.path.dirname(os.path.abspath(__file__))) for path in glob(generated+'/*')]
setup(name=package,version='0.1.0',packages=[package],
      data_files=[('share/ament_index/resource_index/packages',['resource/'+package]),
                  ('share/'+package,['package.xml']),('share/'+package+'/config',glob('config/*')+generated_files)],
      install_requires=['setuptools'],zip_safe=False,maintainer='Ch13',maintainer_email='maintainer@example.invalid',
      description='Generated integrated Piper MoveIt configuration',license='BSD-3-Clause')
