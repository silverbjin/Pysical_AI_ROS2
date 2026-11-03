import rclpy,time
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init();n=Node('inspect_actual_message_info');seen=[]
def cb(msg,info):
 print('MESSAGE_INFO_KEYS',list(info) if isinstance(info,dict) else dir(info),flush=True);seen.append(True)
s=n.create_subscription(String,'/ch13/reuse/info_probe',cb,1);p=n.create_publisher(String,'/ch13/reuse/info_probe',1)
end=time.monotonic()+2
while not seen and time.monotonic()<end:
 p.publish(String(data='probe'));rclpy.spin_once(n,timeout_sec=.05)
print('ENDPOINT_GID_LENGTHS',[len(x.endpoint_gid) for x in n.get_publishers_info_by_topic('/ch13/reuse/info_probe')],flush=True)
n.destroy_node();rclpy.shutdown()
