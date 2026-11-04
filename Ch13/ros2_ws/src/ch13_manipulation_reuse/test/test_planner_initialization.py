"""A slow description lookup must leave the ROS owner free to service its lease."""
import time
from types import SimpleNamespace
from ch13_manipulation_reuse import planning


def test_slow_description_read_does_not_block_owner_heartbeat(tmp_path,monkeypatch):
    (tmp_path/'config').mkdir();(tmp_path/'config/robot.urdf').write_text('<robot name="fixture"/>')
    def slow_share(_):
        time.sleep(.4)
        return str(tmp_path)
    monkeypatch.setattr(planning,'get_package_share_directory',slow_share)
    ticks=[];start=time.monotonic()
    def until(predicate,timeout):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            ticks.append(time.monotonic())
            if predicate():return True
            time.sleep(.005)
        return False
    client=lambda:SimpleNamespace(service_is_ready=lambda:True,server_is_ready=lambda:True,destroy=lambda:None)
    node=SimpleNamespace(create_client=lambda *a:client(),destroy_client=lambda c:None)
    planner=planning.Planner(node,until,lambda:{},action_client_factory=lambda *a:client())
    try:
        assert planner.description=='<robot name="fixture"/>'
        assert max(b-a for a,b in zip([start]+ticks,ticks+[time.monotonic()]))<.1
    finally:planner.close()
