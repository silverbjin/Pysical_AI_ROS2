"""One bounded visual lift correction, using measured robot endpoint lag."""
import math


def lift_correction(baseline_z,observed_z,commanded_tcp_z,measured_tcp_z):
    values=(baseline_z,observed_z,commanded_tcp_z,measured_tcp_z)
    if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite lift feedback')
    deficit=baseline_z+.10-observed_z
    if deficit<=.005:return 0.
    if deficit>.027:raise ValueError('visual lift shortfall exceeds bounded correction')
    lag=max(0.,commanded_tcp_z-measured_tcp_z)
    return min(.03,deficit+.003+lag)
