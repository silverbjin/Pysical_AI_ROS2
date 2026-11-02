"""Closed first-input force reachability, not physical-engine acceptance."""
import hashlib,json,math,sys
import itertools
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0,str(Path.cwd()/'Ch13/ros2_ws/src/integrated_robot_navigation'))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.load_transition import SpatialLoadTransition
from integrated_robot_navigation.contact_equilibrium import skew

fixture=Path('Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_26a3_spatial_budget.json')
data=json.loads(fixture.read_text());a=data['args'];model=compile_model(data['urdf']);feet=model.feet
force=np.array([a['forces_world'][f] for f in feet]).ravel();selected=feet.index(a['foot'])
with NativeMassEvaluator(model) as core:
    kernel=SpatialLoadTransition(model,terms_evaluator=core.contact_terms)
    vertical=kernel.response(a['joints'],a['body_pose'],a['points'])
    stiffness=np.zeros((12,12));body=np.zeros((12,6));pose=np.array(a['body_pose'])
    for i,f in enumerate(feet):
        j=kernel._jacobians[f]
        names=[f[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
        stiffness[3*i:3*i+3,3*i:3*i+3]=np.linalg.inv((j/np.array([kernel.gains[n] for n in names]))@j.T)
        body[3*i:3*i+3]=np.column_stack((np.eye(3),-skew(np.asarray(a['points'][f])-pose[:3,3])))
    product=stiffness@body
    full=-(stiffness-product@np.linalg.solve(body.T@product,product.T))
    full=(full+full.T)/2
    tangent=pose[:3,0].copy();tangent[2]=0.;tangent/=np.linalg.norm(tangent)
    second=np.cross([0.,0.,1.],tangent)
    rows=[]
    for i,f in enumerate(feet):
        normal=np.zeros(12);normal[3*i+2]=-1.;rows.append((normal,0. if i==selected else -2.))
        for axis in (tangent,-tangent,second,-second):
            cone=axis.copy();cone[2]-=1./math.sqrt(2.);row=np.zeros(12);row[3*i:3*i+3]=cone
            rows.append((row,0.))
    space=np.array([row for row,_ in rows]);rhs=np.array([bound for _,bound in rows])-space@force
    objective=np.zeros(12);objective[3*selected+2]=1.
    reports=[]
    choices=[('current_height_only',[2,5,8,11]),('comparison_full_xyz',list(range(12))),
        ('comparison_stance_xyz',[i for i in range(12) if i not in (3*selected,3*selected+1)])]
    for name,columns in choices:
        response=full[:,columns]*.01
        bounds=[]
        for index in columns:
            f=feet[index//3]
            low,high=a['allowed_z'][f];z=a['reference_z'][f];origin=a['origins'][f]
            zbound=((max(low,origin-.01)-z)/.01,(min(high,origin+.01)-z)/.01)
            if f==a['foot']:zbound=(max(0.,zbound[0]),zbound[1])
            bounds.append(zbound if index%3==2 else (-1.,1.))
        ref_rows=[]
        for foot in range(4):
            for signs in itertools.product((-1.,1.),repeat=3):
                row=np.zeros(12);row[3*foot:3*foot+3]=signs;ref_rows.append(row[columns])
        matrix=np.vstack((space@response,ref_rows));limits=np.r_[rhs,np.ones(len(ref_rows))]
        result=linprog(objective@response,A_ub=matrix,b_ub=limits,
            bounds=bounds,method='highs',options=dict(time_limit=.1))
        entry=dict(space=name,rank=int(np.linalg.matrix_rank(response,tol=1e-7)),
            column_indices=columns,reference_l1_cap_m=.01,
            singular_values=np.linalg.svd(response,compute_uv=False).tolist(),status=int(result.status),
            scope='linearized_prediction_force_cone_only_no_torque_rate_or_physical_proof')
        if result.success:
            predicted=force+response@result.x
            entry.update(minimum_selected_normal_n=float(predicted[3*selected+2]),
                selected_force_world=predicted[3*selected:3*selected+3].tolist(),
                max_constraint_residual=float(np.max(space@predicted-np.array([b for _,b in rows]))),
                reference_delta_m=(result.x*.01).tolist())
        reports.append(entry)
report=dict(fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),engine_attempts=0,
    selected=a['foot'],baseline_force_world=a['forces_world'][a['foot']],
    limitations=['fixed first linearization','XYZ is an offline comparison; no runtime policy was changed',
        'motor/rate constraints omitted: this is a relaxation','not measured force response'],results=reports)
output=Path(sys.argv[1]);assert not output.exists();output.write_text(json.dumps(report,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(report,indent=2))
