from setuptools import setup

setup(name='ch14_ai_common', version='0.1.0', packages=['ch14_ai_common'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/ch14_ai_common']),
                  ('share/ch14_ai_common', ['package.xml'])],
      install_requires=['setuptools'], zip_safe=False,
      description='Chapter 14 shared CPU inference and deployment contracts')
