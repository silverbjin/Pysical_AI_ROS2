#include <fstream>
#include <iostream>
#include <iomanip>
#include <nav2_regulated_pure_pursuit_controller/regulated_pure_pursuit_controller.hpp>
class Probe: public nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController {
 public:
 using RegulatedPurePursuitController::getLookAheadPoint;

};
int main(int argc,char** argv) {
 if(argc!=2)return 2;
 std::ifstream input(argv[1]);Probe controller;int label,n;
 std::cout<<std::setprecision(17);
 while(input>>label>>n) {
  nav_msgs::msg::Path path;path.header.frame_id="isolated_reconstruction";
  for(int i=0;i<n;++i) {
   geometry_msgs::msg::PoseStamped p;input>>p.pose.position.x>>p.pose.position.y;
   p.pose.orientation.w=1.;path.poses.push_back(p);
  }
  for(double distance:{.45,.25})for(bool after:{false,true}) {
   const auto p=controller.getLookAheadPoint(distance,path,after);
   std::cout<<label<<" "<<distance<<" "<<after<<" "<<p.pose.position.x<<" "<<p.pose.position.y<<" "<<((p.pose.position.x*p.pose.position.x+p.pose.position.y*p.pose.position.y)>0.001 ? 2*p.pose.position.y/(p.pose.position.x*p.pose.position.x+p.pose.position.y*p.pose.position.y) : 0.)<<"\n";
  }
 }
}
