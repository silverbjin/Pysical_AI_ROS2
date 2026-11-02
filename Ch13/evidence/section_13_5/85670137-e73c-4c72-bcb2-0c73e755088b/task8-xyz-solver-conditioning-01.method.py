import sys,json
from pathlib import Path
import numpy as np
root=Path.cwd();sys.path[:0]=[str(root/'Ch13/ros2_ws/src/integrated_robot_navigation'),str(root/'Ch13/ros2_ws/src/integrated_robot_navigation/test')]
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation import load_xyz as module
from test_spatial_xyz_transition import xyz_inputs
import xacro
model=compile_model(xacro.process_file(str(root/'Ch13/ros2_ws/src/integrated_robot_description/urdf/robot_system.urdf.xacro'),mappings={'hip_mount_y':'0.13'}).toxml())
model,args=xyz_inputs(model)
report=dict(scope='arithmetic_solver_diagnosis_not_engine',geometry='ideal_feedback_with_test_urdf',model_sha256=model.model_sha256)
original=module.minimize
def inspect(fun,x,**kw):
    jac=kw['jac'];h=np.column_stack([jac(x+e)-jac(x) for e in np.eye(len(x))])
    report['hessian_eigenvalues']=np.linalg.eigvalsh(h).tolist();report['initial_gradient']=jac(x).tolist()
    result=original(fun,x,**kw)
    report['solver']=dict(status=int(result.status),nit=int(result.nit),message=str(result.message),
        x=result.x.tolist(),cost=float(result.fun),gradient=np.asarray(result.jac).tolist())
    return result
module.minimize=inspect
with NativeMassEvaluator(model) as core:
    kernel=module.SpatialXYZTransition(model,default_limits(),terms_evaluator=core.contact_terms)
    try:report['delta']=kernel.step(**args)
    except ValueError as error:report['error']=str(error)
    report['attempt']=kernel.last_attempt
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
