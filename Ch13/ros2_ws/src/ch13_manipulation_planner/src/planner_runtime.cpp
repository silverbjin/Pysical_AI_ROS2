// SPDX-License-Identifier: BSD-3-Clause
// Ch13 owns only lifecycle ordering. Planning, IK, collision and trajectory
// execution are the installed, unmodified MoveIt/MoveGroup plugins.
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <moveit/moveit_cpp/moveit_cpp.hpp>
#include <moveit/move_group/move_group_capability.hpp>
#include <moveit/move_group/move_group_context.hpp>
#include <moveit/planning_scene_monitor/planning_scene_monitor.hpp>
#include <moveit/trajectory_execution_manager/trajectory_execution_manager.hpp>
#include <moveit/utils/logger.hpp>
#include <moveit/controller_manager/controller_manager.hpp>
#include <pluginlib/class_loader.hpp>
#include <atomic>
#include <chrono>
#include <csignal>
#include <dlfcn.h>
#include <thread>
#include <vector>

namespace {
volatile std::sig_atomic_t interrupted=0;
void signal_stop(int){interrupted=1;}
}

int main(int argc,char**argv){
  rclcpp::init(argc,argv,rclcpp::InitOptions(),rclcpp::SignalHandlerOptions::None);
  // Callback-group weak control blocks can outlive TEM's plugin loader. Keep
  // the controller code loaded until all nodes/executors below are destroyed.
  void* controller_code=dlopen("libmoveit_simple_controller_manager.so",RTLD_NOW|RTLD_NODELETE);
  if(!controller_code){RCLCPP_ERROR(rclcpp::get_logger("planner_runtime"),"controller library pin failed: %s",dlerror());return 1;}
  std::signal(SIGINT,signal_stop);std::signal(SIGTERM,signal_stop);
  rclcpp::NodeOptions options;
  options.allow_undeclared_parameters(true).automatically_declare_parameters_from_overrides(true);
  auto node=rclcpp::Node::make_shared("reuse_move_group",options);
  moveit::setNodeLoggerName(node->get_name());
  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),2);
  std::thread spinner;
  int result=0;
  try{
    moveit_cpp::MoveItCpp::Options cpp_options(node);
    cpp_options.planning_pipeline_options.pipeline_names={"ompl"};
    cpp_options.planning_pipeline_options.parent_namespace=node->get_effective_namespace()+".planning_pipelines";
    auto moveit_cpp=std::make_shared<moveit_cpp::MoveItCpp>(node,cpp_options);
    auto monitor=moveit_cpp->getPlanningSceneMonitorNonConst();
    if(!monitor->getPlanningScene())throw std::runtime_error("planning scene unavailable");
    auto context=std::make_shared<move_group::MoveGroupContext>(moveit_cpp,"ompl",true,false);
    pluginlib::ClassLoader<move_group::MoveGroupCapability> loader("moveit_ros_move_group","move_group::MoveGroupCapability");
    std::vector<move_group::MoveGroupCapabilityPtr> capabilities;
    for(const auto*name:{"move_group/MoveGroupCartesianPathService","move_group/MoveGroupKinematicsService",
                        "move_group/MoveGroupPlanService",
                        "move_group/MoveGroupStateValidationService","move_group/MoveGroupGetPlanningSceneService",
                        "move_group/ApplyPlanningSceneService"}){
      move_group::MoveGroupCapabilityPtr capability=loader.createUniqueInstance(name);
      capability->setContext(context);capability->initialize();capabilities.push_back(capability);
    }
    std::atomic_bool requested{false};
    auto shutdown=node->create_service<std_srvs::srv::Trigger>("/ch13/reuse/manipulation/planner/shutdown",
      [&requested](const std::shared_ptr<std_srvs::srv::Trigger::Request>,std::shared_ptr<std_srvs::srv::Trigger::Response> reply){
        reply->success=true;reply->message="ordered MoveGroup cleanup requested; engine remains owned by mission";
        requested.store(true);
      });
    executor.add_node(node);
    spinner=std::thread([&executor](){executor.spin();});
    RCLCPP_INFO(node->get_logger(),"PLANNER_READY: standard MoveGroup services, one scene, two executor threads");
    while(!requested.load()&&!interrupted&&rclcpp::ok())std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::this_thread::sleep_for(std::chrono::milliseconds(50)); // allow the Trigger reply to leave the executor
    // Keep ROS and its executor alive until controllers and monitors have stopped.
    context->trajectory_execution_manager_->stopExecution(true);
    monitor->stopPublishingPlanningScene();
    monitor->stopWorldGeometryMonitor();monitor->stopSceneMonitor();monitor->stopStateMonitor();
    executor.cancel();spinner.join();
    capabilities.clear();context.reset();monitor.reset();moveit_cpp.reset();
    shutdown.reset();
    RCLCPP_INFO(node->get_logger(),"PLANNER_JOINED: capabilities and monitors destroyed before ROS shutdown");
  }catch(const std::exception&error){
    RCLCPP_ERROR(node->get_logger(),"planner lifecycle failed: %s",error.what());
    executor.cancel();if(spinner.joinable())spinner.join();result=1;
  }
  node.reset();rclcpp::shutdown();dlclose(controller_code);return result;
}
