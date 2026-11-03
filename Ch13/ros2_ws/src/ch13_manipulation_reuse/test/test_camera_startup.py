"""Real initialization failure must not race the asynchronous frame receiver."""
import time,json
import os
from pathlib import Path
import mujoco
import pytest
from ch13_navigation_reuse.camera_worker import CameraWorker
from ch13_navigation_reuse import camera_worker


def exit_before_startup_outcome(*args):os._exit(7)


def test_failed_startup_releases_named_resources_with_retained_error_traceback(monkeypatch):
    before=set(Path('/dev/shm').glob('sem.mp-*'))
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody/></mujoco>')
    data=mujoco.MjData(model)
    monkeypatch.setattr(camera_worker,'render_process',exit_before_startup_outcome)
    with pytest.raises(RuntimeError) as retained_error:
        CameraWorker(model,data.qpos,lambda *args:None)
    assert retained_error.value.startup_profile
    assert not (set(Path('/dev/shm').glob('sem.mp-*'))-before),'failed constructor retained named semaphores'


def test_child_bootstrap_exit_is_distinguished_from_a_live_warmup_timeout(monkeypatch):
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody/></mujoco>')
    data=mujoco.MjData(model)
    monkeypatch.setattr(camera_worker,'render_process',exit_before_startup_outcome)
    with pytest.raises(RuntimeError,match='exited before startup.*7'):
        CameraWorker(model,data.qpos,lambda *args:None)


def test_child_initialization_failure_is_reported_before_camera_is_returned(monkeypatch,tmp_path):
    model=mujoco.MjModel.from_xml_string('''<mujoco><visual><global offwidth="320" offheight="240"/></visual>
      <worldbody><geom type="plane" size="2 2 .1"/></worldbody></mujoco>''')
    data=mujoco.MjData(model);original=CameraWorker.receive;worker=None
    def delayed_receiver(self):
        # Force the legitimate scheduling order: startup outcome before the
        # frame receiver consumes the queued initialization exception.
        time.sleep(.4);original(self)
    monkeypatch.setattr(CameraWorker,'receive',delayed_receiver)
    try:
        with pytest.raises(RuntimeError,match='reuse_rgbd'):
            worker=CameraWorker(model,data.qpos,lambda *args:None,latest=True,capture_ledger=tmp_path/'captures.json')
        profile=json.loads((tmp_path/'renderer_startup.json').read_text())
        assert profile['events'][-1]['event']=='error'
        assert not any(row['event']=='ready' for row in profile['events'])
    finally:
        if worker is not None:worker.close()
