"""Native bounded QP must preserve the independently implemented problem."""
from copy import deepcopy
import ctypes,importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
from test_spatial_xyz_transition import xyz_inputs
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.contact_equilibrium import leg_terms,leg_jacobian_local,skew
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.reference_envelope import reference_constraints


def assert_independent_primal(model,limits,args,delta,response):
    feet=model.feet;unit=args['speed']*args['dt'];foot=args['foot']
    force=np.array([args['forces_world'][f] for f in feet]);d=np.array([delta[f] for f in feet])
    predicted=force+(response@d.ravel()).reshape(4,3);pose=np.array(args['body_pose'])
    tangent=pose[:3,0].copy();tangent[2]=0.;tangent/=np.linalg.norm(tangent);second=np.cross([0.,0.,1.],tangent)
    jac,gravity=leg_terms(model,args['joints'],pose,args['points'])
    command=args.get('command_joints',args['joints']);reference=np.array(args.get('reference_pose',pose))
    targets={f:np.array(args['reference_xyz'][f])+delta[f] for f in feet}
    for i,f in enumerate(feet):
        assert np.abs(d[i]).sum()<=unit+1e-12
        assert np.abs(targets[f]-args['origins'][f]).sum()<=limits['max_unload_height_m']+1e-12
        lo,hi=args['allowed_z'][f];assert lo-1e-12<=targets[f][2]<=hi+1e-12
        assert predicted[i,2]>=(0. if f==foot else args['min_force'])-1e-7
        for axis in (tangent,-tangent,second,-second):
            assert axis@predicted[i]-predicted[i,2]/np.sqrt(2.)<=1e-7
        names=[f[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')];angles=[command[n] for n in names]
        dq=np.linalg.solve(leg_jacobian_local(model,f,angles,fk_leg(model,f,angles)),reference[:3,:3].T@d[i])
        static=gravity[f]-jac[f].T@predicted[i]
        import xml.etree.ElementTree as ET
        tree=ET.fromstring(model.urdf)
        for k,n in enumerate(names):
            gain=float(tree.find(f"ros2_control/joint[@name='{n}']/param[@name='ch13_kp']").text)
            assert abs(static[k])<=model.limits[n][3]+1e-6
            assert abs(gain*(command[n]-args['joints'][n]+dq[k]))<=model.limits[n][3]+1e-6
    assert np.max(np.abs(d[feet.index(foot),:2]))<=1e-12 and d[feet.index(foot),2]>=-1e-12
    grasp=np.hstack([np.vstack((np.eye(3),skew(np.array(args['points'][f])-pose[:3,3]))) for f in feet])
    assert np.max(np.abs(grasp@(predicted-force).ravel()))<1e-6
    _,clear,bounds=reference_constraints(model,limits,joints=args['joints'],body=reference,targets=targets,
        envelope=args['allowed_z'],selected=foot,future_targets=args['future_targets'])
    assert np.min(clear)>=0. and np.min(bounds)>=0.


def api():
    name='integrated_robot_navigation.native_xyz'
    assert importlib.util.find_spec(name),'bounded QP still crosses Python loops/SLSQP callbacks in the 10ms kernel'
    from integrated_robot_navigation.native_xyz import NativeXYZTransition
    return NativeXYZTransition


@pytest.mark.parametrize('name',['native_c371_xyz_budget.json','native_8d4f_xyz_budget.json','native_141b_xyz_budget.json'])
def test_exact_real_problems_keep_solution_forces_and_original_vector_bounds(name):
    case=json.loads((Path(__file__).parent/'fixtures'/name).read_text());model=compile_model(case['urdf']);a=case['args']
    with NativeMassEvaluator(model) as core:
        oracle=SpatialXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms)
        value=api()(model,case['limits'],terms_evaluator=core.contact_terms)
        try:
            oracle.prepare();value.prepare();expected=oracle.step(**a);actual=value.step(**a)
            assert max(np.max(np.abs(np.array(actual[f])-expected[f])) for f in model.feet)<2e-9
            assert max(np.linalg.norm(v) for v in actual.values())<=a['speed']*a['dt']+1e-12
            assert np.allclose(actual[a['foot']][:2],[0.,0.],atol=1e-12)
            for f in model.feet:
                assert np.allclose(value.last_model['predicted_forces_world'][f],oracle.last_model['predicted_forces_world'][f],atol=1e-5,rtol=0.)
            assert value.last_model['linear_origin_feasible']==oracle.last_model['linear_origin_feasible']
            assert value.last_model['optimization_backend']=='qpmad_1_5_1_native'
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['future_geometry_validated'] is True
        finally:value.close();oracle.close()


def test_failed_or_late_native_math_never_produces_a_reference(nav_robot_model,monkeypatch):
    from integrated_robot_navigation import native_xyz as module
    model,args=xyz_inputs(nav_robot_model);value=api()(model,default_limits())
    try:
        original=value._optimizer.solve;clock=module.time.perf_counter_ns;finished=[False]
        def solve(*a,**kw):
            result=original(*a,**kw);finished[0]=True;return result
        monkeypatch.setattr(value._optimizer,'solve',solve)
        monkeypatch.setattr(module,'time',SimpleNamespace(perf_counter_ns=lambda:clock()+(20_000_000 if finished[0] else 0)))
        with pytest.raises(ValueError,match='time budget'):value.step(**args)
        assert value.last_model is None
    finally:value.close()


def test_infeasible_force_or_closed_owner_cannot_emit_a_reference(nav_robot_model):
    model,args=xyz_inputs(nav_robot_model);value=api()(model,default_limits())
    args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    try:
        with pytest.raises(ValueError,match='transition optimization'):value.step(**args)
        assert value.last_model is None
    finally:value.close()
    with pytest.raises(RuntimeError,match='closed'):value.step(**args)


@pytest.mark.parametrize('name',['native_c371_xyz_budget.json','native_8d4f_xyz_budget.json','native_141b_xyz_budget.json'])
def test_current_jitter_keeps_same_strict_convex_problem_without_warmstart(name):
    case=json.loads((Path(__file__).parent/'fixtures'/name).read_text());model=compile_model(case['urdf']);rng=np.random.default_rng(130601)
    with NativeMassEvaluator(model) as core:
        old=SpatialXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms)
        new=api()(model,case['limits'],terms_evaluator=core.contact_terms)
        try:
            old.prepare();new.prepare()
            for index in range(18):
                args=deepcopy(case['args'])
                for n,value in args['joints'].items():
                    lo,hi=model.limits[n][:2];args['joints'][n]=float(rng.uniform(max(lo,value-.001),min(hi,value+.001)))
                for f,values in args['forces_world'].items():args['forces_world'][f]=(np.array(values)*rng.uniform(.98,1.02)).tolist()
                expected=old.step(**args);actual=new.step(**args)
                response=old.spatial_response(args['joints'],args['body_pose'],args['points'])
                assert np.max(np.abs(new.last_response-response))<1e-6
                unit=args['speed']*args['dt'];a=response*unit;scale=max(float(np.linalg.norm(a,2)**2),1e-12)
                desired=np.array([np.array(args['target_forces'].get(f,[0.,0.,0.]))-args['forces_world'][f] for f in model.feet]).ravel()*args['dt']
                def objective(delta):
                    x=np.array([delta[f] for f in model.feet]).ravel()/unit
                    return float(np.linalg.norm(a@x-desired)**2/scale+.001*(x@x))
                before,after=objective(expected),objective(actual)
                # SLSQP's ftol is a stopping criterion, not a promise of 2nm
                # agreement with an active-set optimum. For the SAME feasible
                # problem, f(old)-f(opt) >= .001*||old-opt||^2 by curvature.
                # Preserve the old failed nm comparison; test the mathematical
                # relation plus an independently reconstructed feasible set.
                assert after<=before+1e-12, dict(index=index,oracle_objective=before,native_objective=after)
                distance=np.linalg.norm(np.array([np.array(actual[f])-expected[f] for f in model.feet]).ravel())
                assert distance<=unit*np.sqrt((max(0.,before-after)+1e-12)/.001)+1e-12
                assert_independent_primal(model,case['limits'],args,actual,response)
                assert all(np.linalg.norm(d)<=args['speed']*args['dt']+1e-12 for d in actual.values())
        finally:new.close();old.close()


def test_preparation_is_idempotent_arithmetic_only(nav_robot_model):
    model,_=xyz_inputs(nav_robot_model);value=api()(model,default_limits())
    try:
        first=value.prepare();assert value.prepare()==first
        assert first['calls']==1 and first['solver_verified'] and value.last_model is None and value.last_attempt is None
    finally:value.close();value.close()


def test_native_dimension_rejection_leaves_reference_output_uncommitted(nav_robot_model):
    model,_=xyz_inputs(nav_robot_model);value=api()(model,default_limits())
    try:
        plan=value._optimizer;data=(ctypes.c_double*175)();out=(ctypes.c_double*208)(*([123.]*208));timing=(ctypes.c_double*8)();error=ctypes.create_string_buffer(1024)
        for count,selected,size in ((174,0,208),(175,4,208),(175,0,207)):
            assert plan._library.ch13_xyz_evaluate(plan._handle,data,count,selected,out,size,timing,8,error,len(error))!=0
            assert list(out)==[123.]*208
    finally:value.close()
