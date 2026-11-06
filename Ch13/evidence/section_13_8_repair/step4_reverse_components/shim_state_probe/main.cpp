#include <nav2_controller/plugins/position_goal_checker.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>
#include <iostream>
int main(int argc,char**argv){
 rclcpp::init(argc,argv);
 auto node=std::make_shared<rclcpp_lifecycle::LifecycleNode>("controller_server");
 nav2_controller::PositionGoalChecker checker;
 checker.initialize(node,".position_checker",nullptr);
 checker.setXYGoalTolerance(.015);
 geometry_msgs::msg::Pose here,goal;geometry_msgs::msg::Twist velocity;
 here.position.x=.012;bool entered=checker.isGoalReached(here,goal,velocity);
 here.position.x=.020;bool drifted=checker.isGoalReached(here,goal,velocity);
 std::cout<<"{\"stateful\":"<<node->get_parameter(".position_checker.stateful").as_bool()<<",\"entered_12mm\":"<<entered<<",\"drifted_20mm\":"<<drifted<<"}"<<std::endl;
 rclcpp::shutdown();return entered&&!drifted?0:1;
}
