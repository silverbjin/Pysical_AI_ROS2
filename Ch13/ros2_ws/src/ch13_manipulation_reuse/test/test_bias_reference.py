import numpy as np
import pytest
from ch13_manipulation_reuse.bias_reference import bias_reference


def test_reference_shift_is_native_pd_plus_model_bias_with_same_gains():
    q=np.array([.1,.2,-.3,.2,-.1,.05]);qd=np.array([.02]*6)
    target=np.array([.12,.22,-.32,.22,-.12,.07]);bias=np.array([0.,3.,-6.,.1,-1.,.1])
    servo=bias_reference(target,bias,50.,np.array([32.,32.,32.,8.,8.,8.]),1.)
    np.testing.assert_allclose(50*(servo-q)-4*qd,50*(target-q)-4*qd+bias,atol=1e-12)
    np.testing.assert_allclose(bias_reference(target,bias,50.,np.array([32.,32.,32.,8.,8.,8.]),0.),target)


def test_nonfinite_bias_or_over_cap_is_not_a_valid_reference():
    for bias in [[0.,0.,float('nan'),0.,0.,0.],[0.,0.,33.,0.,0.,0.]]:
        with pytest.raises(ValueError):bias_reference(np.zeros(6),bias,50.,[32.,32.,32.,8.,8.,8.],1.)
