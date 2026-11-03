"""Explicit 13.6 profile: native PD plus bounded model-bias feedforward.

The internal servo reference is not the planned joint position. Their shift
encodes tau_bias / Kp; the original actuator force limits remain authoritative.
"""
import math
import numpy as np


def bias_reference(target,bias,kp,caps,scale):
    target,bias,caps=(np.asarray(value,dtype=float) for value in (target,bias,caps))
    if (any(value.shape!=(6,) for value in (target,bias,caps))
            or not all(np.isfinite(value).all() for value in (target,bias,caps))
            or not math.isfinite(kp) or kp<=0 or not math.isfinite(scale) or not 0<=scale<=1
            or np.any(caps<=0) or np.any(abs(bias)>caps)):
        raise ValueError('nonfinite or over-cap model bias')
    return target+scale*bias/kp
