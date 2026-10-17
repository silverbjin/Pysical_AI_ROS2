"""Opt-in real graphics tests: CH12_TEST_RENDER=1 MUJOCO_GL=egl pytest."""
import os
import threading
import time
import weakref

import numpy as np
import pytest

from quadruped_rl import QuadrupedEnv


def test_close_waits_for_async_viewer_cleanup():
    class Simulation:
        pass
    class AsyncViewer:
        def __init__(self):
            self.holder = [Simulation()]
            self._sim = weakref.ref(self.holder[0])
        def close(self):
            def finish():
                time.sleep(.03)
                self.holder.clear()
            threading.Thread(target=finish).start()
    with QuadrupedEnv() as env:
        handle = AsyncViewer()
        env._viewer = handle
        env.close()
        assert handle._sim() is None
        assert env._viewer is None
        env.close()


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
