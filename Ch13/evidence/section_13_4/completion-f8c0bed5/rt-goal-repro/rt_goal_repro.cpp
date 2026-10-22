// Ch13 regression: real rclcpp action server/client, no fabricated motor result.
#include <chrono>
#include <iostream>
#include <memory>
#include "control_msgs/action/follow_joint_trajectory.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#ifdef CH13_PATCHED
#include "integrated_robot_controller/realtime_server_goal_handle.hpp"
namespace rt = ch13_realtime_tools;
#else
#include "realtime_tools/realtime_server_goal_handle.hpp"
namespace rt = realtime_tools;
#endif
using namespace std::chrono_literals;
using Action = control_msgs::action::FollowJointTrajectory;
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("ch13_rt_terminal_race_probe");
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::shared_ptr<rt::RealtimeServerGoalHandle<Action>> realtime;
  auto server=rclcpp_action::create_server<Action>(node,"probe",
    [](const auto &,const auto &){return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;},
    [](const auto &){return rclcpp_action::CancelResponse::ACCEPT;},
    [&](auto handle){
      realtime=std::make_shared<rt::RealtimeServerGoalHandle<Action>>(handle);
      realtime->execute();
    });
  auto client=rclcpp_action::create_client<Action>(node,"probe");
  if(!client->wait_for_action_server(2s)) return 2;
  auto accepted=client->async_send_goal(Action::Goal());
  if(executor.spin_until_future_complete(accepted,2s)!=rclcpp::FutureReturnCode::SUCCESS) return 3;
  auto handle=accepted.get();
  auto result=client->async_get_result(handle);
  auto pump=[&](auto duration){
    auto end=std::chrono::steady_clock::now()+duration;
    while(std::chrono::steady_clock::now()<end) executor.spin_once(1ms);
  };
  pump(30ms); // server has the result request before the terminal race
  realtime->setSucceeded(std::make_shared<Action::Result>());
  auto canceled=client->async_cancel_goal(handle);
  if(executor.spin_until_future_complete(canceled,2s)!=rclcpp::FutureReturnCode::SUCCESS) return 4;
  // JTC cleared its RT active pointer after setSucceeded; its non-RT timer
  // still owns this wrapper, and runs after the cancel callback returned.
  realtime->runNonRealtime();
  auto completion=executor.spin_until_future_complete(result,500ms);
  bool terminal=completion==rclcpp::FutureReturnCode::SUCCESS;
  int code=terminal?static_cast<int>(result.get().code):-1;
  std::cout<<"{\"cancel_ack\":"<<static_cast<int>(canceled.get()->return_code)
           <<",\"terminal_result\":"<<(terminal?"true":"false")
           <<",\"result_code\":"<<code
           <<",\"server_canceling\":"<<(realtime->gh_->is_canceling()?"true":"false")<<"}"<<std::endl;
  bool pass=terminal && result.get().code==rclcpp_action::ResultCode::CANCELED;
  executor.remove_node(node);
  server.reset(); client.reset(); realtime.reset(); node.reset();
  rclcpp::shutdown();
  return pass?0:1;
}
