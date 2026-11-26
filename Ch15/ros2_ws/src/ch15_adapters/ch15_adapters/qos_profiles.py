from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
def profile(depth=1,reliable=True,transient=False):
    return QoSProfile(history=HistoryPolicy.KEEP_LAST,depth=depth,reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.TRANSIENT_LOCAL if transient else DurabilityPolicy.VOLATILE)
sensor_qos=profile(reliable=False)
state_qos=profile(10,transient=True)
