"""Small ROS-independent conversion for the figure's IMU pose."""
import math


def pose_components(quaternion_xyzw, position_xyz, orientation_available=True):
    """Validate sensor orientation and copy it once into the reference frame.

    This function assumes the IMU reports orientation relative to odom and is
    aligned with base_link, as in the zero-yaw Gazebo spawn used by this figure.
    Translation comes from TF; no TF rotation is multiplied into the IMU again.
    """
    if not orientation_available:
        raise ValueError('IMU orientation unavailable (covariance[0] == -1)')
    if len(quaternion_xyzw) != 4 or len(position_xyz) != 3:
        raise ValueError('Expected XYZW quaternion and XYZ position')
    q = tuple(float(v) for v in quaternion_xyzw)
    p = tuple(float(v) for v in position_xyz)
    if not all(math.isfinite(v) for v in q + p):
        raise ValueError('Nonfinite IMU orientation or TF position')
    norm = math.sqrt(sum(v*v for v in q))
    if abs(norm-1.0) > 0.05:
        raise ValueError('IMU quaternion is not close to unit length')
    return p, tuple(v/norm for v in q)
