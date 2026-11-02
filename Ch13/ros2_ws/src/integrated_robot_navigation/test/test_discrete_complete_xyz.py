"""Actual failure replay with a verified actuator model, without relaxing caps."""
import json
from pathlib import Path
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition

@pytest.mark.parametrize('fixture',['native_d504_infeasible.json','native_ab85_infeasible.json'])
def test_discrete_model_can_propose_bounded_step_from_recorded_failure(fixture):
    f=json.loads((Path(__file__).parent/'fixtures'/fixture).read_bytes());model=compile_model(f['urdf'])
    with NativeMassEvaluator(model) as mass:
        k=CompleteXYZTransition(model,f['limits'],native_mass=mass,force_model='gazebo_discrete_equilibrium_v1')
        try:
            k.prepare();delta=k.step(**f['args']);proof=k.last_model
            assert proof['force_model']=='gazebo_discrete_equilibrium_v1'
            assert proof['all_actuator_caps_validated'] is True
            assert proof['actuator_count']==20
            assert proof['compute_wall_ns']<=10_000_000 and proof['optimization_iterations']<=32
            assert max(np.linalg.norm(d,ord=1) for d in delta.values())<=f['args']['speed']*f['args']['dt']+1e-12
            assert delta[f['args']['foot']][0:2]==[0.,0.]
            assert delta[f['args']['foot']][2]>=0.
            assert proof['future_geometry_validated'] is True
            selected=f['args']['foot']
            assert proof['predicted_forces_world'][selected][2]<f['args']['forces_world'][selected][2]-1e-4
            assert proof['inequality_residual']<=1e-7
            assert all(abs(t)<=model.limits[n][3]+1e-6 for n,t in proof['bounded_actuator_efforts'].items())
            # Reconstruct all20 predicted commands outside the QP in the
            # independent joint order, so a wrong native index/unit cannot
            # pass merely by asserting the emitted proof flag.
            from integrated_robot_navigation.native_equilibrium import NativeEquilibrium
            from integrated_robot_navigation.leg_kinematics import _leg_spec,fk_leg
            from integrated_robot_navigation.contact_equilibrium import leg_jacobian_local
            a=f['args'];increment=[]
            for foot in model.feet:
                names=_leg_spec(model.urdf,foot)[4];angles=[a['command_joints'][n] for n in names]
                jac=np.asarray(a['reference_pose'])[:3,:3]@leg_jacobian_local(model,foot,angles,fk_leg(model,foot,angles))
                increment.extend(np.linalg.solve(jac,delta[foot]))
            with NativeEquilibrium(model.urdf) as independent:
                force=np.asarray([a['forces_world'][foot] for foot in model.feet]).ravel()
                r=independent.evaluate(joints=a['joints'],body_pose=a['body_pose'],command_joints=a['command_joints'],forces=force)
                dq=r['position_derivative'][6:]@increment;dc=np.zeros(len(independent.names))
                dc[independent.plan['leg_indices']]=increment
                gain=np.array(independent.plan['gains']);caps=np.array(independent.plan['effort'])
                raw=gain*np.array([a['command_joints'][n]-a['joints'][n] for n in independent.names])
                commanded=np.clip(raw,-caps,caps)+(np.abs(raw)<caps)*gain*(dc-dq)
                assert np.max(np.abs(commanded)-caps)<=1e-6
                predicted=force+r['force_derivative']@increment
                np.testing.assert_allclose(predicted.reshape(4,3),[proof['predicted_forces_world'][foot] for foot in model.feet],atol=1e-7,rtol=1e-7)

        finally:k.close()


def test_discrete_actual_child_verifies_library_and_normal_receipt_close():
    import hashlib
    from integrated_robot_navigation.load_process import SpatialLoadProcess,assess_numeric_close,assess_numeric_jobs
    from integrated_robot_navigation.native_equilibrium import equilibrium_library_path
    f=json.loads((Path(__file__).parent/'fixtures/native_d504_infeasible.json').read_bytes());model=compile_model(f['urdf'])
    worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=f['limits'],
        receipt_mode='event_receiver',force_model='gazebo_discrete_equilibrium_v1')
    try:
        ready=worker.prepare()
        assert ready['force_model']=='gazebo_discrete_equilibrium_v1'
        assert ready['equilibrium_library_sha256']==hashlib.sha256(equilibrium_library_path().read_bytes()).hexdigest()
        reply=worker.transact(f['args'],{'generation':0})
        assert reply['context']=={'generation':0} and reply['job_id']==1
        assert worker.last_model['equilibrium_library_sha256']==ready['equilibrium_library_sha256']
        assert worker.last_model['all_actuator_caps_validated'] is True
        assert worker.last_transaction['wall_ns']<=10_000_000
        assert assess_numeric_jobs(worker.snapshot())
    finally:closed=worker.close()
    assert closed['receiver_joined'] and closed['receiver_slot_empty'] and closed['acknowledged']
    closed.update(model_sha256=model.model_sha256,owner_pid=closed['pid']+1)
    assert assess_numeric_close(closed,model.model_sha256)
