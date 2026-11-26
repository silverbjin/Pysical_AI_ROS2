from setuptools import setup
setup(name="ch14_rl_deployment",version="0.1.0",packages=["ch14_rl_deployment"],
 data_files=[("share/ament_index/resource_index/packages",["resource/ch14_rl_deployment"]),("share/ch14_rl_deployment",["package.xml"])],
 install_requires=["setuptools"],zip_safe=False,
 entry_points={"console_scripts":["rl_shadow=ch14_rl_deployment.shadow_node:main"]})
