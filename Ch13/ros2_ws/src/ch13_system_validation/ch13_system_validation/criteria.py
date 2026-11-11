"""Named performance policies; no actuator, collision or lease parameters."""
from dataclasses import asdict, dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Criteria:
    profile: str
    success_rate_min: float
    mean_sim_s_max: float
    position_error_m_max: float
    maximum_tilt_rad: float
    mean_cpu_percent_max: float

    def record(self):
        return asdict(self)


PROFILES = MappingProxyType({
    'book_v1': Criteria('book_v1', .9, 120., .03, .1, 70.),
    'education_v1': Criteria('education_v1', .8, 600., .10, .15, 85.),
})


def get_criteria(profile='book_v1'):
    try:
        return PROFILES[profile]
    except (KeyError, TypeError):
        raise ValueError('unknown evaluation criteria profile: '+str(profile)) from None
