"""A level moving frame over an explicitly known horizontal ground plane."""
import math
from my_quadruped_bot.sensors.attitude_history import unit


def level_pose(position, quaternion, ground_height=0.0):
    if len(position) != 3 or not all(math.isfinite(v) for v in (*position, ground_height)):
        raise ValueError('Invalid position/ground height')
    x, y, z, w = unit(quaternion)
    yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
    return (position[0], position[1], ground_height), (0, 0, math.sin(yaw/2), math.cos(yaw/2))
