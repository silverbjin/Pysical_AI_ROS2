"""Share private, immutable observation values without renewing either clock."""
from types import MappingProxyType
import numpy as np

from integrated_robot_navigation.samples import Sample


def _freeze(value):
    if isinstance(value, MappingProxyType):
        return value
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError('observation keys must be strings')
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) in (tuple, list):
        frozen = tuple(_freeze(item) for item in value)
        if type(value) is tuple and all(a is b for a, b in zip(value, frozen)):
            return value
        return frozen
    if type(value) in (str, int, float, bool, type(None)):
        return value
    # Generated ROS fixed-length numeric arrays expose NumPy scalar values.
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return _freeze(value.item())
    raise TypeError('unsupported observation value: ' + type(value).__name__)


def freeze_sample(sample):
    data = _freeze(sample.data)
    if data is sample.data:
        return sample
    return Sample(sample.stamp_ns, sample.received_ns, sample.epoch,
                  sample.sequence, sample.frame_id, data)


def sample_record(sample):
    if sample is None:
        return None
    value = freeze_sample(sample)
    # A fresh root mapping also preserves project_body's mutable copy contract.
    data = dict(value.data) if isinstance(value.data, MappingProxyType) else value.data
    return dict(stamp_ns=value.stamp_ns, received_ns=value.received_ns,
                epoch=value.epoch, sequence=value.sequence,
                frame_id=value.frame_id, data=data)


def json_value(value):
    if isinstance(value, MappingProxyType):
        return dict(value)
    raise TypeError('unsupported JSON observation value: ' + type(value).__name__)
