from ch13_system_validation.physics import assess_transport


def rows():
    data=[]
    for i in range(101):
        phase='CARRY' if i<50 else 'RETREAT'
        point=[1.-i*.02,0.,.64] if i<50 else [-.55,0.,.54]
        data.append(dict(sim_s=i*.1,phase=phase,target=point,relative_tcp=[0.,0.,0.],
                         target_contact_N={'link7':.1,'link8':.1} if i<50 else {'link7':0.,'link8':0.},
                         target_support_N=0. if i<50 else .19))
    return data


def test_transport_requires_physical_carry_and_released_supported_object():
    assert assess_transport(rows())['result']=='PASS'
    data=rows();data[-1]['target_support_N']=0.
    assert assess_transport(data)['result']=='FAIL'


def test_transport_drop_and_short_or_missing_release_fail():
    data=rows();data[30]['target'][2]=.4
    assert assess_transport(data)['result']=='FAIL'
    assert assess_transport(rows()[:51])['result']=='FAIL'
    assert assess_transport([])['result']=='FAIL'


def test_nonfinite_contact_force_is_not_physical_success():
    data=rows();data[10]['target_contact_N']['link7']=float('inf')
    assert assess_transport(data)['result']=='FAIL'
