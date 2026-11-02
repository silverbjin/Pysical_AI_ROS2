"""Bound live observer memory, preserve ALL samples for post-engine checks."""
import json
import gc
import rclpy
import pytest
from rclpy.context import Context
from probe_navigation_13_5 import NavigationProbe


def test_g2_archive_is_bounded_live_and_restores_every_original_record_after_join(tmp_path):
    context=Context();rclpy.init(context=context);probe=None
    callbacks=tuple(gc.callbacks)
    try:
        probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
        for index in range(600):
            row=dict(ros_ns=index,wall_ns=index+10,stage='forward',samples={'original':index})
            probe._write('frame',row);probe.frames.append(row)
            row=dict(capture_ns=index,sequence=index,stage='forward',original={'value':index})
            probe._write('native_controls',row);probe.native_controls.append(row)
            # This test measures cache preservation, not sink overload. The
            # separate capacity tests deliberately cover an undrained burst.
            if index%64==63:probe.flush_log()
        assert len(probe.frames)<=128 and len(probe.native_controls)<=128
        assert probe.latest_frame()['ros_ns']==599
        with pytest.raises(RuntimeError,match='joined'):probe.restore_history(receiver_joined=False)
        probe.restore_history(receiver_joined=True)
        assert [row['ros_ns'] for row in probe.frames]==list(range(600))
        assert [row['capture_ns'] for row in probe.native_controls]==list(range(600))
        assert probe.native_controls[0]['original']=={'value':0}
        assert tuple(gc.callbacks)==callbacks,'global diagnostic callback leaked after live observation'
    finally:
        if probe is not None:probe.close_log();probe.destroy_node()
        context.try_shutdown()


@pytest.mark.parametrize('damage',['truncated','missing'])
def test_g2_archive_corruption_never_passes_by_checking_only_recent_cache(tmp_path,damage):
    context=Context();rclpy.init(context=context);probe=None
    try:
        probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
        probe._write('frame',dict(ros_ns=1));probe.frames.append(dict(ros_ns=1));probe.flush_log()
        path=tmp_path/'observations.jsonl'
        if damage=='truncated':
            with path.open('a') as output:output.write('{broken')
        else:path.write_text('')
        with pytest.raises((ValueError,RuntimeError),match='journal|record|JSON|Expecting'):
            probe.restore_history(receiver_joined=True)
    finally:
        if probe is not None:probe.close_log();probe.destroy_node()
        context.try_shutdown()
