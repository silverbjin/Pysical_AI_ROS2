"""Same current/future geometry through an owned, immutable C ABI plan."""
from copy import deepcopy
import ctypes,importlib.util,json
from pathlib import Path
import numpy as np
import pytest
from test_compiled_reference import fixture,assert_same
from integrated_robot_navigation.leg_kinematics import fk_leg


def api():
    name='integrated_robot_navigation.native_reference'
    assert importlib.util.find_spec(name),'current 28-point geometry remains in Python inside the 10ms job'
    from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
    return NativeReferenceEnvelope


@pytest.mark.parametrize('name',['native_c371_xyz_budget.json','native_8d4f_xyz_budget.json'])
def test_exact_recorded_input_preserves_all_current_and_future_residuals(name):
    from integrated_robot_navigation.model import compile_model
    case=json.loads((Path(__file__).parent/'fixtures'/name).read_text());data=case['args']
    model,limits=compile_model(case['urdf']),case['limits']
    a=dict(joints=data['joints'],body=data['reference_pose'],targets=data['reference_xyz'],
        envelope=data['allowed_z'],selected=data['foot'],future_targets=data['future_targets'])
    with api()(model,limits) as value:
        assert_same(model,limits,value,a)
        assert value.provenance['abi']==1 and value.provenance['samples']==28
        assert len(value.provenance['library_sha256'])==64


def test_random_current_inputs_keep_independent_python_geometry_parity():
    model,limits,a=fixture();rng=np.random.default_rng(1305308)
    with api()(model,limits) as value:
        for index in range(100):
            q=dict(a['joints']);body=np.eye(4);angle=rng.uniform(-.2,.2)
            body[:2,:2]=[[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]
            body[:3,3]=rng.uniform(-.2,.2,3);targets={}
            for f in model.feet:
                angles=[rng.uniform(-.15,.15),rng.uniform(-.8,-.4),rng.uniform(.9,1.5)]
                for part,v in zip(('hip','thigh','calf'),angles):q[f[:2]+'_'+part+'_joint']=v
                targets[f]=(body@np.r_[fk_leg(model,f,angles),1.])[:3]
            future=deepcopy(targets);selected=model.feet[index%4];future[selected][:2]+=[.001,-.001]
            args=dict(joints=q,body=body,targets=targets,envelope={f:(p[2]-.0005,p[2]+.0005) for f,p in targets.items()},
                selected=selected,future_targets=future)
            assert_same(model,limits,value,args)


@pytest.mark.parametrize('bad',['target_nan','future_nan','envelope_nan','missing_foot','unreachable','bad_joint','body_singular'])
def test_invalid_current_inputs_fail_closed(bad):
    model,limits,a=fixture();f=a['selected']
    if bad=='target_nan':a['targets'][f][0]=float('nan')
    elif bad=='future_nan':a['future_targets'][f][0]=float('nan')
    elif bad=='envelope_nan':a['envelope'][f]=[0.,float('nan')]
    elif bad=='missing_foot':del a['targets'][f]
    elif bad=='unreachable':a['future_targets'][f][0]+=1.
    elif bad=='body_singular':a['body']=np.zeros((4,4))
    else:a['joints']['fr_hip_joint']=10.
    with api()(model,limits) as value:
        with pytest.raises(ValueError):value.evaluate(**a)


def test_closed_handle_cannot_evaluate_and_close_is_idempotent():
    model,limits,a=fixture();value=api()(model,limits);value.close();value.close()
    with pytest.raises(RuntimeError,match='closed'):value.evaluate(**a)


def test_native_call_rejects_invalid_dimensions_without_writing_outputs():
    model,limits,a=fixture()
    with api()(model,limits) as value:
        inputs=(ctypes.c_double*60)();out=(ctypes.c_double*40)(*([123.]*40))
        function=value._library.ch13_reference_evaluate
        for count,selected,size in ((59,0,40),(60,4,40),(60,0,39)):
            assert function(value._handle,inputs,count,selected,out,size)!=0
            assert list(out)==[123.]*40
