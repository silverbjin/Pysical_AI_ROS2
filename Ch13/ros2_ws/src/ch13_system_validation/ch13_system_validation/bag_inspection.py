"""Offline CDR inspection following rosbag2 0.26.11 rosbag2csv.py."""
import json,math
from collections import Counter
from pathlib import Path
import yaml
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

N='/ch13/reuse'
CORE_TOPICS=('/clock','/tf','/tf_static',N+'/joint_states',N+'/odometry',N+'/cmd_vel_safe',
             N+'/vision/observation',N+'/vision/health',N+'/manipulation/status',N+'/navigation/status',
             N+'/validation/bt_log','/start_mission')


def inspect_bag(path,required_topics=CORE_TOPICS):
    path=Path(path).resolve()
    metadata=yaml.safe_load((path/'metadata.yaml').read_text())['rosbag2_bagfile_information']
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(path)),rosbag2_py.ConverterOptions('',''))
    types={topic.name:topic.type for topic in reader.get_all_topics_and_types()}
    counts=Counter();first=None;last=None;ordered=True;observations_valid=True;observations=0
    while reader.has_next():
        topic,data,stamp=reader.read_next();counts[topic]+=1
        if first is None:first=stamp
        if last is not None and stamp<last:ordered=False
        last=stamp
        if topic==N+'/vision/observation':
            message=deserialize_message(data,get_message(types[topic]));sample=json.loads(message.data)
            observations+=1
            observations_valid &= (type(sample.get('capture_ns')) is int and sample['capture_ns']>0
                and len(sample.get('point',[]))==3 and all(math.isfinite(v) for v in sample['point'])
                and bool(sample.get('source_gids')) and len(sample.get('rgb_sha256',''))==64)
    del reader
    missing=sorted(set(required_topics)-set(counts))
    total=sum(counts.values());matches=metadata['message_count']==total
    checks=dict(required_topics=not missing,metadata_count_matches=matches,ordered_record_time=ordered,
                nonempty=total>0,observation_payload=observations_valid)
    return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,counts=dict(counts),
                message_count=total,duration_ns=None if first is None else last-first,missing_topics=missing,
                observation_samples=observations,storage=metadata['storage_identifier'],
                scope='recording integrity only; no ROS node or live mission authority')
