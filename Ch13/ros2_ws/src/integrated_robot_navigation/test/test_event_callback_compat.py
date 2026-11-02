"""Two public executor calling conventions preserve exact payload identities."""
import asyncio
import inspect
import pytest
from integrated_robot_navigation import dispatch_node as api


@pytest.mark.parametrize('asynchronous',[False,True])
def test_callback_info_adapter_retains_required_signature_and_original_objects(asynchronous):
    assert hasattr(api,'event_compatible_callback'),'MessageInfo compatibility missing'
    if asynchronous:
        async def original(msg,info):return msg,info
    else:
        def original(msg,info):return msg,info
    callback=api.event_compatible_callback(original)
    assert inspect.iscoroutinefunction(callback)==asynchronous
    with pytest.raises(TypeError):inspect.signature(callback).bind(None)
    message=object();info={'source_timestamp':123,'publisher_gid':object()}
    for args in (((message,info),),(message,info)):
        result=callback(*args)
        if asynchronous:result=asyncio.run(result)
        assert result[0] is message and result[1] is info
    with pytest.raises(TypeError):callback() if not asynchronous else asyncio.run(callback())


def test_optional_bound_stream_callback_keeps_original_message_only_semantics():
    assert hasattr(api,'event_compatible_callback'),'MessageInfo compatibility missing'
    def original(msg,stream='joints'):return msg,stream
    assert api.event_compatible_callback(original) is original
