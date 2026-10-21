"""8.7: ReachEnv 전용 RGB 이미지 캡처 어댑터 (실기 제어 없음)."""
import mujoco
from rl_env import ReachEnv


class ReachRGBEnv(ReachEnv):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 100}

    def __init__(self, width=640, height=480):
        super().__init__(render_mode=None)
        self.render_mode = "rgb_array"
        self._renderer = mujoco.Renderer(self.model, height=height, width=width)

    def render(self):
        self._renderer.update_scene(self.data)
        return self._renderer.render().copy()

    def close(self):
        try:
            self._renderer.close()
        finally:
            super().close()
