// Uses the installed Ch13 actuator/observation implementation on its real URDF.
// Finite stationary perturbations only. No ROS integration/G1/C1/G2 acceptance.
#include <gz/sim/TestFixture.hh>
#include <gz/sim/Server.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/Name.hh>
#include <gz_ros2_control/gz_system_interface.hpp>
#include <hardware_interface/component_parser.hpp>
#include <pluginlib/class_loader.hpp>
#include <rclcpp/rclcpp.hpp>
#include <nlohmann/json.hpp>
#include <fstream>
#include <sstream>
#include <array>
#include <map>
#include <set>
#include <vector>
#include <cmath>
#include <iostream>
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include "integrated_robot_navigation_sensors/dart_contact.hpp"
namespace sim=gz::sim;
namespace c=sim::components;
namespace nav=integrated_robot_navigation_sensors;
using Json=nlohmann::json;
using Base=gz_ros2_control::GazeboSimSystemInterface;
using Return=hardware_interface::return_type;
Json pose_json(sim::Entity model,const sim::EntityComponentManager &ecm) {
 const auto p=sim::worldPose(sim::Model(model).CanonicalLink(ecm),ecm);
 return {{"position",{p.Pos().X(),p.Pos().Y(),p.Pos().Z()}},
  {"orientation",{p.Rot().X(),p.Rot().Y(),p.Rot().Z(),p.Rot().W()}}};
}
struct Summary {
 size_t count=0;std::array<double,12> force{},squared{};
 std::map<std::string,double> q,qd;double max_abs_qd=0.;
 void add(const Json &controls,const Json &contacts) {
  ++count;
  if(contacts.at("feet").size()!=4) throw std::runtime_error("four feet required");
  for(size_t f=0;f<4;++f) {
   const auto &row=contacts.at("feet").at(f);
   if(row.at("force_on_collision_valid")!=true || row.at("sum_abs_force1_world_z_n").get<double>()<2.)
    throw std::runtime_error("lost support in stationary diagnostic");
   for(size_t a=0;a<3;++a) {double v=row.at("sum_force_on_collision_world_n").at(a);force[3*f+a]+=v;squared[3*f+a]+=v*v;}
  }
  for(const auto &row:controls.at("joints")) {
   const std::string name=row.at("name");double position=row.at("position"),velocity=row.at("velocity");
   q[name]+=position;qd[name]+=velocity;max_abs_qd=std::max(max_abs_qd,std::abs(velocity));
   if(row.contains("position_reference")) {
    const double applied=row.at("position_reference").at("applied");
    if(!std::isfinite(applied)) throw std::runtime_error("nonfinite applied reference");
   }
  }
 }
 Json finish(size_t condition,const std::map<std::string,double> &target,const Json &pose)const {
  if(count!=100) throw std::runtime_error("fixed100 mean samples required");
  std::array<double,12> f{},sd{};Json positions=Json::object(),velocities=Json::object();
  for(size_t i=0;i<12;++i) {f[i]=force[i]/count;sd[i]=std::sqrt(std::max(0.,squared[i]/count-f[i]*f[i]));}
  for(const auto &[name,v]:q) positions[name]=v/count;
  for(const auto &[name,v]:qd) velocities[name]=v/count;
  return {{"condition",condition},{"samples",count},{"target",target},{"mean_forces_world_flat",f},
    {"force_std_flat",sd},{"mean_joint_positions",positions},{"mean_joint_velocities",velocities},
    {"max_abs_joint_velocity_rps",max_abs_qd},{"last_body",pose}};
 }
};
int main(int argc,char **argv) {
 if(argc!=3) return 2;
 std::ifstream in(argv[2]);Json config;in>>config;
 rclcpp::init(0,nullptr);
 constexpr size_t warmup=5000,per_case=1000;
 const std::array<std::string,4> feet{"fr_foot","fl_foot","rr_foot","rl_foot"};
 std::vector<std::string> leg_names;
 for(const auto &prefix:{"fr","fl","rr","rl"}) for(const auto &part:{"hip","thigh","calf"})
  leg_names.push_back(std::string(prefix)+"_"+part+"_joint");
 Json perturbations=Json::array();perturbations.push_back(Json::object());
 if(config.contains("perturbations")) perturbations=config.at("perturbations");
 else for(const auto &name:leg_names) for(double sign:{1.,-1.}) perturbations.push_back({{name,sign*2e-5}});
 const size_t cases=perturbations.size(),total=warmup+per_case*cases;
 const size_t ramp_steps=config.value("input_ramp_steps",size_t(0));
 size_t step=0;bool configured=false,run_ok=false,destroyed=false;
 sim::Entity model=sim::kNullEntity;Json reports=Json::array(),baseline,library_paths=Json::array();
 std::string error;
 const auto contact=nav::configure_g1_dart_contact(.00005,1,true);
 {
  pluginlib::ClassLoader<Base> loader("gz_ros2_control","gz_ros2_control::GazeboSimSystemInterface");
  auto system=loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  auto node=std::make_shared<rclcpp::Node>("ch13_stationary_force_response_diagnostic");
  auto infos=hardware_interface::parse_control_resources_from_urdf(config.at("control_urdf"));
  if(infos.size()!=1) throw std::runtime_error("one original hardware block required");
  auto info=infos.front();
  std::map<std::string,double> target=config.at("targets").get<std::map<std::string,double>>();
  auto last_sent=target,case_start=target;
  for(auto &joint:info.joints) for(auto &state:joint.state_interfaces) if(state.name=="position")
   state.initial_value=config.at("seed_joints").at(joint.name).dump();
  std::vector<hardware_interface::CommandInterface> commands;Summary summary;
  try {
   sim::TestFixture fixture(argv[1]);
   fixture.OnPreUpdate([&](const sim::UpdateInfo &u,sim::EntityComponentManager &ecm) {
    if(u.paused || u.dt!=std::chrono::milliseconds(2)) throw std::runtime_error("fixed2ms required");
    if(!configured) {
     model=ecm.EntityByComponents(c::Model(),c::Name(config.at("model_name").get<std::string>()));
     if(!model) throw std::runtime_error("actual model absent");
     std::map<std::string,sim::Entity> native;
     for(const auto &joint:info.joints) {
      auto entity=ecm.EntityByComponents(c::Joint(),c::Name(joint.name));
      if(!entity) throw std::runtime_error("actual native joint absent");native[joint.name]=entity;
     }
     if(!system->initSim(node,native,info,ecm,100)) throw std::runtime_error("actual PositionPDSystem init rejected");
     commands=system->export_command_interfaces();std::vector<std::string> start;
     for(auto &command:commands) start.push_back(command.get_name());
     if(system->perform_command_mode_switch(start,{})!=Return::OK) throw std::runtime_error("activation rejected");
     nav::request_gazebo_observations(model,ecm);configured=true;
    }
    size_t condition=step<warmup?0:(step-warmup)/per_case;
    if(step>=warmup && (step-warmup)%per_case==0) {summary=Summary();case_start=last_sent;}
    auto desired=target;
    for(auto it=perturbations.at(condition).begin();it!=perturbations.at(condition).end();++it) desired.at(it.key())+=it.value().get<double>();
    const size_t local=step<warmup?0:(step-warmup)%per_case;
    const double weight=step<warmup || !ramp_steps?1.:std::min(1.,static_cast<double>(local+1)/ramp_steps);
    // The installed leg20ms reference interpolation and physical cap remain.
    for(auto &command:commands) {
     auto name=command.get_name();name=name.substr(0,name.rfind('/'));
     const double value=case_start.at(name)*(1.-weight)+desired.at(name)*weight;
     if(!command.set_value(value)) throw std::runtime_error("command handle rejected");
     last_sent[name]=value;
    }
    const auto stamp=std::chrono::duration_cast<std::chrono::nanoseconds>(u.simTime).count();
    if(system->write(rclcpp::Time(stamp,RCL_ROS_TIME),rclcpp::Duration::from_seconds(.002))!=Return::OK)
     throw std::runtime_error("installed actuator write fault");
   }).OnPostUpdate([&](const sim::UpdateInfo &u,const sim::EntityComponentManager &ecm) {
    if(step>=warmup && (step-warmup)%per_case>=per_case-100) {
     auto controls=nav::read_gazebo_controls_json(model,ecm,u.simTime,step+1,false);
     auto contacts=nav::read_gazebo_contact_reference_json(model,ecm,u.simTime,false);
     if(!controls || !contacts) throw std::runtime_error("actual measurements missing");
     summary.add(*controls,*contacts);
     if((step-warmup)%per_case==per_case-1) {
      size_t condition=(step-warmup)/per_case;auto desired=target;
      for(auto it=perturbations.at(condition).begin();it!=perturbations.at(condition).end();++it) desired.at(it.key())+=it.value().get<double>();
      reports.push_back(summary.finish(condition,desired,pose_json(model,ecm)));
      if(condition==0) baseline={{"controls",*controls},{"contacts",*contacts},{"body",pose_json(model,ecm)}};
     }
    }
    ++step;
   }).Finalize();
   run_ok=fixture.Server()->Run(true,total,false);fixture.Server()->Stop();
  } catch(const std::exception &e) {error=e.what();}
  destroyed=true; // scoped TestFixture destruction returned before reporting
  std::ifstream maps("/proc/self/maps");std::string line;std::set<std::string> paths;
  while(std::getline(maps,line)) if(line.find("libnavigation_position_system.so")!=std::string::npos ||
    line.find("libdart.so.")!=std::string::npos) {std::istringstream fields(line);std::string token,last;while(fields>>token) last=token;paths.insert(last);}
  for(const auto &path:paths) library_paths.push_back(path);
  std::vector<std::string> stop;for(auto &command:commands) stop.push_back(command.get_name());
  if(configured) system->perform_command_mode_switch({},stop);
 }
 rclcpp::shutdown();
 bool completed=run_ok && destroyed && step==total && reports.size()==cases && error.empty();
 std::cout<<Json({{"scope","actual_URDF_installed_PD_stationary_physics_component_not_G1_C1_G2"},
  {"run_ok",run_ok},{"server_destroyed",destroyed},{"completed",completed},{"error",error},{"steps",step},
  {"baseline",baseline},{"cases",reports},{"input_joint_delta_rad",2e-5},{"leg_names",leg_names},
  {"perturbations",perturbations},{"input_ramp_steps",ramp_steps},
  {"mapped_libraries",library_paths},{"physics_dt_s",.002},{"contact_allowance_m",contact.effective_m},
  {"DART_provider",contact.library_path},{"ROS_shutdown",!rclcpp::ok()}}).dump(2)<<'\n';
 return completed?0:1;
}
