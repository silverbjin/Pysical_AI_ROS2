// Ch13 DDS metadata boundary. No physics, policy, hardware or global settings.
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/serialization.hpp>
#include <rclcpp/serialized_message.hpp>
#include <std_msgs/msg/string.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <time.h>
#include <string>
#include <vector>
static std::string hex(const uint8_t* data,size_t n) {
  static const char* digits="0123456789abcdef";
  std::string out;out.reserve(2*n);
  for(size_t i=0;i<n;++i){out+=digits[data[i]>>4];out+=digits[data[i]&15];}
  return out;
}
class Ingress:public rclcpp::Node {
  using Packet=std_msgs::msg::String;
  std::vector<rclcpp::SubscriptionBase::SharedPtr> subscriptions_;
  rclcpp::Publisher<Packet>::SharedPtr gateway_,platform_;
  template<class T> void connect(const std::string& key,const std::string& topic,
      rclcpp::Publisher<Packet>::SharedPtr destination) {
    subscriptions_.push_back(create_subscription<T>(topic,rclcpp::SensorDataQoS().keep_last(1),
      [key,destination](typename T::ConstSharedPtr message,const rclcpp::MessageInfo& info) {
        timespec receipt{};clock_gettime(CLOCK_MONOTONIC,&receipt);
        const auto wall_ns=int64_t(receipt.tv_sec)*1000000000LL+receipt.tv_nsec;
        const auto& rmw=info.get_rmw_message_info();
        rclcpp::Serialization<T> serialization;rclcpp::SerializedMessage serialized;
        serialization.serialize_message(message.get(),&serialized);
        const auto& cdr=serialized.get_rcl_serialized_message();
        if(cdr.buffer_length>65536)return; // bounded ingress, never unbounded queues
        const auto relay_gid=destination->get_gid();
        Packet packet;
        packet.data="r2v1|"+key+"|"+hex(rmw.publisher_gid.data,RMW_GID_STORAGE_SIZE)+"|"+
          hex(relay_gid.data,RMW_GID_STORAGE_SIZE)+"|"+std::to_string(wall_ns)+"|"+
          std::to_string(rmw.source_timestamp)+"|"+hex(cdr.buffer,cdr.buffer_length);
        destination->publish(packet);
      }));
  }
public:
  Ingress():Node("ch13_reuse_ingress") {
    gateway_=create_publisher<Packet>("/ch13/reuse/ingress/gateway",16);
    platform_=create_publisher<Packet>("/ch13/reuse/ingress/platform",16);
    connect<rosgraph_msgs::msg::Clock>("clock","/clock",gateway_);
    connect<nav_msgs::msg::Odometry>("base","/ch13/reuse/engine_state",gateway_);
    connect<sensor_msgs::msg::JointState>("joints","/ch13/reuse/joint_states",gateway_);
    connect<geometry_msgs::msg::TwistStamped>("raw","/ch13/reuse/cmd_vel_raw",gateway_);
    connect<geometry_msgs::msg::TwistStamped>("safe","/ch13/reuse/cmd_vel_safe",platform_);
  }
};
int main(int argc,char**argv){rclcpp::init(argc,argv);rclcpp::spin(std::make_shared<Ingress>());rclcpp::shutdown();return 0;}
