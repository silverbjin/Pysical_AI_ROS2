// SPDX-License-Identifier: Apache-2.0
// Original serialized ROS reception; no commands, TF, state or clock publishers.
#include "integrated_robot_navigation_sensors/cdr_journal.hpp"
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/create_timer.hpp>
#include <rclcpp/generic_subscription.hpp>
#include <rclcpp/serialization.hpp>
#include <integrated_robot_interfaces/msg/motion_state.hpp>
#include <tf2_msgs/msg/tf_message.hpp>
#include <poll.h>
#include <atomic>
#include <chrono>
#include <algorithm>
#include <csignal>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <iomanip>

using Json=nlohmann::json;
using integrated_robot_navigation_sensors::CdrJournal;
static std::mutex output_mutex;
static void reply(const std::string & kind,const Json & value) {
  std::lock_guard<std::mutex> lock(output_mutex);std::cout<<Json::array({kind,value}).dump()<<std::endl;
}
static int64_t steady_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
}
static int64_t system_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::system_clock::now().time_since_epoch()).count();
}
static std::string gid_hex(const rmw_gid_t & gid) {
  std::ostringstream out;out<<std::hex<<std::setfill('0');
  for(auto byte:gid.data) {out<<std::setw(2)<<unsigned(byte);}return out.str();
}

class EvidenceRecorder:public rclcpp::Node {
public:
  EvidenceRecorder(CdrJournal & journal,const std::string & engine)
  : Node("navigation_native_cdr_observer",rclcpp::NodeOptions().use_global_arguments(false)
      .parameter_overrides({rclcpp::Parameter("use_sim_time",true)})),journal_(journal) {
    const auto sensor=rclcpp::SensorDataQoS();
    add("joints","/joint_states","sensor_msgs/msg/JointState",sensor);
    add("imu","/navigation/imu","sensor_msgs/msg/Imu",sensor);
    add("contacts","/navigation/foot_contacts","integrated_robot_interfaces/msg/FootContacts",sensor);
    add("body","/odom","nav_msgs/msg/Odometry",sensor);
    add("scan","/scan","sensor_msgs/msg/LaserScan",sensor);
    add("carry","/navigation/carry_state","integrated_robot_interfaces/msg/MotionState",sensor);
    add("native_com","/navigation/native_com","geometry_msgs/msg/PoseStamped",sensor);
    add("native_controls","/navigation/native_controls","std_msgs/msg/String",rclcpp::QoS(100));
    if(engine=="mujoco") {
      add("body_source","/native/free_joint_states","mujoco_ros2_control_msgs/msg/FreeJointStateArray",sensor);
      add("applied_reference","/navigation/applied_reference","sensor_msgs/msg/JointState",rclcpp::QoS(1));
    }
    for(const auto * key:{"crawl","carry","guard","startup"}) {
      add(std::string(key)+"_state",std::string("/navigation/")+key+"_state",
        "integrated_robot_interfaces/msg/MotionState",rclcpp::QoS(10));
    }
    add("tf","/tf","tf2_msgs/msg/TFMessage",sensor);
    add("tf_static","/tf_static","tf2_msgs/msg/TFMessage",rclcpp::QoS(1).transient_local());
    timer_=rclcpp::create_timer(this,get_clock(),rclcpp::Duration::from_seconds(.02),[this] {
      const auto wall=steady_ns();std::lock_guard<std::mutex> lock(state_mutex_);
      if(!journal_.submit({{"kind","frame"},{"ros_ns",get_clock()->now().nanoseconds()},
          {"wall_ns",wall},{"stage",stage_}})) {fault("native CDR frame enqueue failed");}
    });
  }
  void stage(const std::string & value) {
    const std::vector<std::string> valid={"bootstrap","stand","calibrate","forward","left","right","reverse","stopped","shutdown"};
    if(std::find(valid.begin(),valid.end(),value)==valid.end()) {throw std::runtime_error("unknown observer stage");}
    std::lock_guard<std::mutex> lock(state_mutex_);stage_=value;
    if(!journal_.submit({{"kind","stage"},{"stage",stage_},{"wall_ns",steady_ns()}})) {
      throw std::runtime_error("native CDR stage enqueue failed");
    }
  }
  Json transforms() {
    std::deque<std::pair<std::shared_ptr<const rclcpp::SerializedMessage>,std::string>> cache;
    {std::lock_guard<std::mutex> lock(state_mutex_);cache=tf_cache_;}
    Json result=Json::array();rclcpp::Serialization<tf2_msgs::msg::TFMessage> serializer;
    for(const auto & entry:cache) {
      tf2_msgs::msg::TFMessage message;serializer.deserialize_message(entry.first.get(),&message);
      for(const auto & tf:message.transforms) {
        result.push_back({{"parent",tf.header.frame_id},{"child",tf.child_frame_id},{"gid",entry.second},
          {"stamp_ns",int64_t(tf.header.stamp.sec)*1000000000+tf.header.stamp.nanosec}});
      }
    }
    if(result.size()>128) {result.erase(result.begin(),result.end()-128);}return result;
  }
  Json runtime_fault() {std::lock_guard<std::mutex> lock(state_mutex_);return runtime_fault_;}
private:
  void fault(const std::string & reason) {
    if(stage_=="shutdown" || !runtime_fault_.is_null()) {return;}
    runtime_fault_={{"reason",reason},{"stage",stage_},{"ros_ns",get_clock()->now().nanoseconds()},
      {"wall_ns",steady_ns()}};reply("fault",runtime_fault_);
  }
  void add(const std::string & key,const std::string & topic,const std::string & type,const rclcpp::QoS & qos) {
    subscriptions_.push_back(create_generic_subscription(topic,type,qos,
      [this,key](std::shared_ptr<const rclcpp::SerializedMessage> data,const rclcpp::MessageInfo & info) {
        const auto wall=steady_ns(),system=system_ns();
        try {
          const auto & rmw=info.get_rmw_message_info();const auto gid=gid_hex(rmw.publisher_gid);
          std::lock_guard<std::mutex> lock(state_mutex_);
          if(!journal_.submit({{"kind","packet"},{"key",key},{"received_ns",wall},
              {"callback_system_ns",system},{"source_system_ns",rmw.source_timestamp},
              {"rmw_received_system_ns",rmw.received_timestamp},{"gid",gid},{"stage",stage_}},data)) {
            fault("native CDR packet enqueue failed");
          }
          if(key=="tf" || key=="tf_static") {
            tf_cache_.emplace_back(data,gid);if(tf_cache_.size()>128) {tf_cache_.pop_front();}
          }
          if(key.size()>6 && key.compare(key.size()-6,6,"_state")==0) {
            integrated_robot_interfaces::msg::MotionState message;
            rclcpp::Serialization<integrated_robot_interfaces::msg::MotionState> serializer;
            serializer.deserialize_message(data.get(),&message);
            if(!message.fault_reason.empty()) {fault(key+":"+message.fault_reason);}
          }
        } catch(const std::exception & error) {
          std::lock_guard<std::mutex> lock(state_mutex_);fault(std::string("native CDR callback:")+error.what());
        }
      }));
  }
  CdrJournal & journal_;std::mutex state_mutex_;std::string stage_="bootstrap";
  Json runtime_fault_=nullptr;
  std::vector<rclcpp::GenericSubscription::SharedPtr> subscriptions_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::deque<std::pair<std::shared_ptr<const rclcpp::SerializedMessage>,std::string>> tf_cache_;
};

int main(int argc,char ** argv) {
  std::atomic<bool> stopping{false},normal_stop{false};std::thread commands;
  std::string failure,report_path;Json runtime_fault=nullptr;std::unique_ptr<CdrJournal> journal;
  std::shared_ptr<EvidenceRecorder> node;
  std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> executor;
  bool receiver_closed=false;
  try {
    std::signal(SIGPIPE,SIG_IGN);  // An absent parent is a failed drain, not an abrupt signal exit.
    rclcpp::init(argc,argv);const auto args=rclcpp::remove_ros_arguments(argc,argv);
    if(args.size()!=3 || (args[2]!="mujoco" && args[2]!="gazebo")) {
      throw std::invalid_argument("usage: navigation_evidence_recorder NEW_OUTPUT.cdr mujoco|gazebo");
    }
    journal=std::make_unique<CdrJournal>(args[1]);
    report_path=(std::filesystem::path(args[1]).parent_path()/"observer_native_report.json").string();
    node=std::make_shared<EvidenceRecorder>(*journal,args[2]);
    executor=std::make_unique<rclcpp::executors::SingleThreadedExecutor>();executor->add_node(node);
    commands=std::thread([&] {
      std::string buffer;
      try {
        while(!stopping.load()) {
          pollfd input{STDIN_FILENO,POLLIN,0};const auto result=::poll(&input,1,100);
          if(result<0 && errno==EINTR) {continue;}
          if(result<0) {throw std::runtime_error("observer command poll");}
          if(!result) {continue;}
          char bytes[4096];const auto count=::read(STDIN_FILENO,bytes,sizeof(bytes));
          if(count<=0) {throw std::runtime_error("observer parent connection closed");}
          buffer.append(bytes,count);if(buffer.size()>65536) {throw std::runtime_error("observer command capacity");}
          size_t end;
          while((end=buffer.find('\n'))!=std::string::npos) {
            const auto command=Json::parse(buffer.substr(0,end));buffer.erase(0,end+1);
            const auto kind=command.at(0).get<std::string>();
            if(kind=="stage") {const auto value=command.at(1).get<std::string>();node->stage(value);reply("stage",value);}
            else if(kind=="transforms") {reply("transforms",node->transforms());}
            else if(kind=="stop") {normal_stop=true;stopping=true;break;}
            else {throw std::runtime_error("unknown observer command");}
          }
        }
      } catch(const std::exception & error) {failure=error.what();stopping=true;reply("error",failure);}
    });
    reply("ready",{{"pid",getpid()},{"uid",getuid()},{"backend","native_cdr"},
      {"node_ready_wall_ns",steady_ns()}});
    while(!stopping.load() && rclcpp::ok()) {executor->spin_once(std::chrono::milliseconds(100));}
    stopping=true;commands.join();runtime_fault=node->runtime_fault();
    executor->remove_node(node);executor.reset();node.reset();receiver_closed=true;
    journal->close();rclcpp::shutdown();
    if(!normal_stop.load() && failure.empty()) {failure="observer exited without parent stop";}
  } catch(const std::exception & error) {
    failure=error.what();stopping=true;if(commands.joinable()) {commands.join();}
    if(node) {executor.reset();node.reset();receiver_closed=true;}
    if(journal) {journal->close();}rclcpp::shutdown();
  }
  const auto journal_report=journal?journal->report():Json::object();
  if(journal && !journal_report.at("error").get<std::string>().empty() && failure.empty()) {
    failure=journal_report.at("error").get<std::string>();
  }
  Json closed={{"failure",failure},{"runtime_fault",runtime_fault},{"journal",journal_report},
    {"receiver",{{"closed",receiver_closed},{"executor","rclcpp_single_threaded"}}},{"ros_closed",!rclcpp::ok()}};
  if(!report_path.empty()) {
    const int descriptor=::open(report_path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    bool written=descriptor>=0;
    if(written) {
      const auto text=closed.dump(2)+"\n";size_t offset=0;
      while(offset<text.size()) {
        const auto count=::write(descriptor,text.data()+offset,text.size()-offset);
        if(count<0 && errno==EINTR) {continue;}
        if(count<=0) {written=false;break;}offset+=static_cast<size_t>(count);
      }
      if(::close(descriptor)!=0) {written=false;}
    }
    if(!written) {failure+=" native report write failed";closed["failure"]=failure;}
  }
  reply("closed",closed);
  return failure.empty()?0:1;
}
