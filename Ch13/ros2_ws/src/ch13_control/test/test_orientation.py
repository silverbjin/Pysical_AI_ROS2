from types import SimpleNamespace
import math
from ch13_control.common import base_tilt

def test_yaw_is_not_roll_pitch_tilt():
    assert base_tilt(SimpleNamespace(w=math.cos(.5),x=0.,y=0.,z=math.sin(.5)))==0.
    assert abs(base_tilt(SimpleNamespace(w=math.cos(.1),x=math.sin(.1),y=0.,z=0.))-.2)<1e-8
