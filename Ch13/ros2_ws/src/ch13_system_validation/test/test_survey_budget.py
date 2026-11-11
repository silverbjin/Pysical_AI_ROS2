import pytest


def test_budget_start_uses_actual_task_port_without_overwriting_its_wall_stamp():
    from ch13_system_validation.survey_budget import SurveyBudget
    from ch13_mission_orchestration.tasks import TaskPort
    port=TaskPort()
    SurveyBudget(clock_ns=10,wall=5.).record_start(port)
    event=port.snapshot()['events'][-1]
    assert event['event']=='survey_budget_started'
    assert event['budget_start_wall']==5.
    assert event['clock_ns']==10
    assert event['sim_budget_s']==120 and event['wall_budget_s']==240
    assert 'wall' in event


def test_survey_uses_both_existing_action_limits_instead_of_a_realtime_assumption():
    from ch13_system_validation.survey_budget import SurveyBudget
    budget=SurveyBudget(clock_ns=10_000_000_000,wall=100.)
    assert budget.reason(clock_ns=41_000_000_000,wall=220.) is None
    assert budget.reason(clock_ns=129_999_999_999,wall=339.999) is None
    assert budget.reason(clock_ns=130_000_000_000,wall=339.999)=='sim_deadline'


def test_a_stopped_simulation_still_hits_the_wall_deadline():
    from ch13_system_validation.survey_budget import SurveyBudget
    assert SurveyBudget(clock_ns=10,wall=5.).reason(clock_ns=10,wall=245.)=='wall_deadline'


@pytest.mark.parametrize('clock,wall', [(9,6.), (10,4.), (None,6.), (10,float('nan'))])
def test_invalid_or_reversing_time_never_grants_more_survey_authority(clock,wall):
    from ch13_system_validation.survey_budget import SurveyBudget
    with pytest.raises(ValueError):SurveyBudget(clock_ns=10,wall=5.).reason(clock_ns=clock,wall=wall)
