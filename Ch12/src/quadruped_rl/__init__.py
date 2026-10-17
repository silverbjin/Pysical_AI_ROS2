"""Chapter 12.1 MuJoCo lab; importing does not open a window."""
from .env import QuadrupedEnv
from .training_env import QuadrupedTrainingEnv
from .locomotion_env import QuadrupedLocomotionEnv
from .rewards import RewardConfig

__all__ = ["QuadrupedEnv", "QuadrupedTrainingEnv", "QuadrupedLocomotionEnv", "RewardConfig"]
