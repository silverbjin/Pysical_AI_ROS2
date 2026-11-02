"""All privileged effects are fake; exercise rollback before real operations."""
from copy import deepcopy
import pytest
from temporary_clock_lease import ClockLease

class Ops:
    def __init__(self):
        self.tick=9166;self.boot='boot-a';self.calls=[];self.fail=None
        self.states={d:dict(active='active',enabled='enabled',boot='boot-a',namespace='time:1',clock_ticks=100) for d in ('Ubuntu-22.04','Ubuntu-24.04')}
    def inspect(self,d):return deepcopy(self.states[d])
    def clock(self):return dict(tick_us=self.tick,freq_scaled_ppm=2111682,status=0,boot_id=self.boot)
    def service(self,d,action):
        self.calls.append((d,action))
        self.states[d]['active']='inactive' if action=='stop' else 'active'
        if self.fail==(d,action):raise RuntimeError('service failure')
    def set_tick(self,expected,target,boot):
        assert self.tick==expected and self.boot==boot
        self.calls.append(('tick',expected,target))
        self.tick=target
        if self.fail=='after_write' and target==10000:raise RuntimeError('lost write response')

def lease(ops):
    journal=[]
    return ClockLease(ops,lambda value:journal.append(deepcopy(value))),journal

def test_normal_lease_records_before_write_and_restores_all_owned_changes():
    ops=Ops();owner,journal=lease(ops);owner.begin()
    assert ops.tick==10000
    assert all(v['active']=='inactive' for v in ops.states.values())
    assert any(r.get('tick_write_attempted') and r['restoration_pending'] for r in journal)
    assert owner.close() is True
    assert ops.tick==9166 and all(v['active']=='active' for v in ops.states.values())
    assert owner.record['restored'] and not owner.record['restoration_pending']

@pytest.mark.parametrize('field,value',[('boot','other'),('namespace','other'),('clock_ticks',250),('active','inactive')])
def test_unapproved_initial_environment_does_not_change_anything(field,value):
    ops=Ops();ops.states['Ubuntu-22.04'][field]=value;owner,_=lease(ops)
    with pytest.raises(RuntimeError):owner.begin()
    assert not ops.calls

def test_unexpected_initial_tick_does_not_change_anything():
    ops=Ops();ops.tick=9500;owner,_=lease(ops)
    with pytest.raises(RuntimeError):owner.begin()
    assert not ops.calls

def test_partial_stop_failure_restores_every_attempted_service():
    ops=Ops();ops.fail=('Ubuntu-24.04','stop');owner,_=lease(ops)
    with pytest.raises(RuntimeError):owner.begin()
    assert owner.close()
    assert ops.tick==9166 and all(v['active']=='active' for v in ops.states.values())

def test_lost_write_response_still_restores_original_tick_and_services():
    ops=Ops();ops.fail='after_write';owner,_=lease(ops)
    with pytest.raises(RuntimeError):owner.begin()
    assert ops.tick==10000
    assert owner.close() and ops.tick==9166

def test_external_tick_writer_is_not_overwritten_and_is_reported_pending():
    ops=Ops();owner,_=lease(ops);owner.begin();ops.tick=9500
    assert owner.close() is False
    assert ops.tick==9500 and owner.record['restoration_pending']
    assert all(v['active']=='active' for v in ops.states.values())

def test_boot_change_does_not_operate_on_replacement_instance():
    ops=Ops();owner,_=lease(ops);owner.begin();ops.boot='boot-b'
    before=len(ops.calls)
    assert owner.close() is False
    assert len(ops.calls)==before and owner.record['restoration_pending']

def test_restoration_failure_is_not_hidden_by_other_service_success():
    ops=Ops();owner,_=lease(ops);owner.begin();ops.fail=('Ubuntu-22.04','start')
    assert owner.close() is False
    assert ('Ubuntu-24.04','start') in ops.calls and owner.record['errors']

@pytest.mark.parametrize('initial_tick',[9166,9167,9500,10000,10833])
def test_service_only_comparison_does_not_write_over_chrony_owned_tick(initial_tick):
    ops=Ops();ops.tick=initial_tick;journal=[]
    owner=ClockLease(ops,lambda r:journal.append(deepcopy(r)),normalize_tick=False)
    owner.begin()
    assert all(v['active']=='inactive' for v in ops.states.values())
    ops.tick=10000  # The unmodified clock owner naturally finishes its slew.
    assert owner.close() is True
    assert ops.tick==10000 and not any(c[0]=='tick' for c in ops.calls)
    assert owner.record['tick_write_attempted'] is False

def test_rejected_initial_environment_has_no_restoration_debt():
    ops=Ops();ops.states['Ubuntu-22.04']['boot']='different';owner,_=lease(ops)
    with pytest.raises(RuntimeError):owner.begin()
    assert owner.close() is True
    assert owner.record['restored'] and not owner.record['restoration_pending']
    assert not ops.calls


def test_same_shared_kernel_boot_does_not_authorize_a_replacement_distro_init():
    ops=Ops()
    for value in ops.states.values():value['init_start_ticks']=10
    owner,_=lease(ops);owner.begin()
    ops.states['Ubuntu-22.04']['init_start_ticks']=200
    assert owner.close() is False
    assert ('Ubuntu-22.04','start') not in ops.calls
    assert owner.record['restoration_pending']
