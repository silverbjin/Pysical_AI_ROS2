import copy
import uuid
import pytest


def test_world_witness_requires_actual_ramp_contact_or_door_passage_and_fresh_find():
    from ch13_system_validation.world_assessment import assess_world
    from ch13_system_validation.scenarios import get_scenario
    rows=[dict(base_xyz=[x,.2,.3],ramp_contact_N=10.) for x in (0.,.6,1.2,2.)]
    assert assess_world(rows,get_scenario('level2_obstacles'),found=True)['result']=='PASS'
    assert assess_world([dict(r,ramp_contact_N=0.) for r in rows],get_scenario('level2_obstacles'),found=True)['result']=='FAIL'
    assert assess_world(rows,get_scenario('level3_house'),found=True)['result']=='PASS'
    assert assess_world([dict(r,base_xyz=[r['base_xyz'][0],1.,.3]) for r in rows],get_scenario('level3_house'),found=True)['result']=='FAIL'
    assert assess_world(rows,get_scenario('level3_house'),found=False)['result']=='FAIL'


def data():
    from ch13_system_validation.batch import make_plan
    plan=make_plan('a'*64,{'level2_obstacles':'b'*64,'level3_house':'c'*64},
                   identities=[str(uuid.UUID(int=i+1)) for i in range(10)])
    rows=[dict(uuid=s['uuid'],scenario=s['scenario'],scenario_sha256=s['scenario_sha256'],
        source_manifest_sha256=plan['source_manifest_sha256'],profile='actual',complete=True,success=True,
        sim_s=100.,wall_s=240.,position_error_m=.02,max_tilt_rad=.08,cpu_percent=60.,
        physical={'world':{'result':'PASS'}}) for s in plan['slots']]
    return plan,rows


def test_fixed_schedule_has_five_each_and_failure_is_not_replaced_or_removed():
    from ch13_system_validation.batch import assess_batch
    plan,rows=data()
    assert [s['scenario'] for s in plan['slots']]==['level2_obstacles','level3_house']*5
    rows[0]['success']=False
    result=assess_batch(plan,rows)
    assert result['success_rate']==.9 and result['attempts']==10
    rows.pop()
    result=assess_batch(plan,rows)
    assert result['result']=='FAIL' and result['expected']==10
    assert result['success_rate']==.8 and len(result['missing'])==1
    assert result['mean_sim_s'] is None


@pytest.mark.parametrize('kind', ['source','scenario','uuid','world','mock','nan'])
def test_batch_rejects_substituted_or_unproven_attempts(kind):
    from ch13_system_validation.batch import assess_batch
    plan,rows=data()
    rows=copy.deepcopy(rows)
    if kind=='source':rows[0]['source_manifest_sha256']='d'*64
    if kind=='scenario':rows[0]['scenario_sha256']='d'*64
    if kind=='uuid':rows[0]['uuid']=str(uuid.uuid4())
    if kind=='world':rows[0]['physical']['world']['result']='FAIL'
    if kind=='mock':rows[0]['profile']='mock'
    if kind=='nan':rows[0]['sim_s']=float('nan')
    assert assess_batch(plan,rows)['result']=='FAIL'


def test_duplicate_slots_or_trials_are_rejected_before_aggregation():
    from ch13_system_validation.batch import make_plan,assess_batch
    plan,rows=data()
    with pytest.raises(ValueError):make_plan('a'*64,{'level2_obstacles':'b'*64,'level3_house':'c'*64},identities=['same']*10)
    with pytest.raises(ValueError):assess_batch(plan,rows+[rows[0]])
