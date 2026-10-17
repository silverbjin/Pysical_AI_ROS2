"""Opt-in real graphics tests: CH12_TEST_RENDER=1 MUJOCO_GL=egl pytest."""
import os

import numpy as np
import pytest

from quadruped_rl import QuadrupedEnv


@pytest.mark.skipif(os.environ.get('CH12_TEST_RENDER') != '1',
                    reason='Requires a working OpenGL context')
def test_rgb_renderer_produces_nonuniform_pixels_and_reopens():
    env = QuadrupedEnv(render_mode='rgb_array')
    try:
        env.reset(seed=0)
        pixels = env.render()
        assert pixels.shape == (480, 640, 3)
        assert pixels.dtype == np.uint8
        assert pixels.std() > 5
        env.close()
        env.close()
        assert env.render().shape == (480, 640, 3)
    finally:
        env.close()
