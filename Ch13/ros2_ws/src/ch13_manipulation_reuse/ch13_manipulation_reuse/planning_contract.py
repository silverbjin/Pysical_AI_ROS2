"""Admission checks independent of planner success or controller tolerance."""
import math
import numpy as np


def cartesian_complete(fraction,error_code,endpoint_error_m):
    return (math.isfinite(fraction) and 1.-1e-6<=fraction<=1.+1e-6 and error_code==1
            and math.isfinite(endpoint_error_m) and 0<=endpoint_error_m<=.005)


def execution_admission(planned_revision,current_revision,planned_start,actual_start,
                        capture_ns,clock_ns,capture_wall,wall):
    a,b=np.asarray(planned_start),np.asarray(actual_start)
    return bool(planned_revision==current_revision and a.shape==b.shape==(6,)
                and np.isfinite(a).all() and np.isfinite(b).all() and max(abs(a-b))<=.025
                and type(capture_ns) is int and type(clock_ns) is int and capture_ns>0
                and -25_000_000<=clock_ns-capture_ns<=300_000_000
                and all(math.isfinite(x) for x in (capture_wall,wall)) and 0<=wall-capture_wall<=.30)
