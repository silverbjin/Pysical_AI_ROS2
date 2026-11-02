"""Intermittent crawl separates four-foot body travel from one-foot swing."""
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_gait import machine


def test_body_reference_holds_after_measured_unload_until_landing(nav_robot_model):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    held=None;checks=0
    for _ in range(2000):
        result=value.advance(plant.state,(.007,0.,.02),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if result.phase=='SWING':
            if held is None:held=value.reference_body.copy()
            else:
                assert np.allclose(value.reference_body,held,atol=1e-12,rtol=0.), \
                    'body moved after measured settle/unload while a foot was swinging'
                checks+=1
        elif held is not None and result.phase in ('TOUCHDOWN','SETTLE'):
            assert np.allclose(value.reference_body,held,atol=1e-12,rtol=0.)
        elif held is not None and result.phase=='SHIFT':
            assert checks>10
            return
        plant.tick(value,result)
    pytest.fail('bounded ideal replay did not complete a held-body swing')
