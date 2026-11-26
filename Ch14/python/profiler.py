#!/usr/bin/env python3
# Code 14-13, canonical utilities.
from ch14_ai_common.profiler import PerformanceMonitor,stage_metrics,ros_age_ms
if __name__=="__main__":
    import time
    m=PerformanceMonitor()
    for _ in range(3):
        t=m.start();time.sleep(.01);m.stop(t);m.published()
    print(m.get_stats())
