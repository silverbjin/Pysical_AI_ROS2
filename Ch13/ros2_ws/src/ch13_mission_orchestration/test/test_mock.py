from ch13_mission_orchestration.mock import run_mock


def test_mock_fetch_contains_return_but_is_explicitly_simulated():
    r=run_mock('normal'); assert r['profile']=='mock' and r['terminal']=='SUCCESS'
    assert r['requested']==['navigate','find','pick','return','finish']


def test_mock_low_battery_preempts_navigation_then_charges_without_pick():
    r=run_mock('low_battery'); assert r['terminal']=='ABORTED'
    assert r['requested']==['navigate','charge']
    assert any(t['nodes'].get('Fetch')=='INVALID' for t in r['ticks'])


def test_mock_fallen_recovers_before_fetch():
    r=run_mock('fallen'); assert r['terminal']=='SUCCESS'
    assert r['requested'][0:2]==['recover','navigate']


def test_mock_missing_object_never_picks_or_returns():
    r=run_mock('not_found'); assert r['terminal']=='FAILURE'
    assert r['requested']==['navigate','find']
