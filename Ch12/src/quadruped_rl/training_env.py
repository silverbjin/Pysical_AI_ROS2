"""Section 12.2 defaults, keeping the section 12.1 class backward compatible."""
from .env import QuadrupedEnv


class QuadrupedTrainingEnv(QuadrupedEnv):
    """31 observations, 50 Hz control, bounded position servos and a free base."""

    def __init__(self, render_mode=None, **kwargs):
        settings = dict(observation_mode="quaternion", control_mode="position",
                        frame_skip=10, initial_height=.5, termination_height=.2)
        settings.update(kwargs)
        super().__init__(render_mode=render_mode, **settings)
