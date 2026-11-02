"""Bounded book-example acceptance policy, separate from physical safety."""
import math

BOOK_REQUIRED_SCENARIOS = ('crawl-cycle', 'crawl-reverse')


def calibration_timeout_s(limits):
    """Only startup patience changes; legacy explicit profiles retain10s.

    Freshness, measured settling, actuator bounds and sticky faults remain
    independent. This lease is fixed once at the initial request.
    """
    value = limits.get('calibration_wall_timeout_s', 10.)
    if type(value) not in (int, float) or not math.isfinite(value) or not 10. <= value <= 20.:
        raise ValueError('calibration_wall_timeout_s must be finite within10..20')
    return float(value)
