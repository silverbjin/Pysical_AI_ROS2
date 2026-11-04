import json
import rosbag2_py
from std_msgs.msg import String
from rclpy.serialization import serialize_message
from ch13_system_validation.bag_inspection import inspect_bag


def make_bag(path):
    writer=rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=str(path),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    writer.create_topic(rosbag2_py.TopicMetadata(id=0,name='/recorded_observation',type='std_msgs/msg/String',serialization_format='cdr'))
    writer.write('/recorded_observation',serialize_message(String(data=json.dumps({'capture_ns':100}))),100)
    writer.write('/recorded_observation',serialize_message(String(data=json.dumps({'capture_ns':200}))),200)
    del writer


def test_actual_cdr_bag_is_read_without_starting_a_ros_node(tmp_path):
    path=tmp_path/'bag';make_bag(path)
    result=inspect_bag(path,required_topics=('/recorded_observation',))
    assert result['result']=='PASS'
    assert result['counts']=={'/recorded_observation':2}
    assert result['message_count']==2
    assert result['duration_ns']==100


def test_missing_required_sensor_topic_is_not_recording_success(tmp_path):
    path=tmp_path/'bag';make_bag(path)
    result=inspect_bag(path,required_topics=('/scan',))
    assert result['result']=='FAIL'
    assert result['missing_topics']==['/scan']
