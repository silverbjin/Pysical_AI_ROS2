// READ-ONLY Gazebo Sim8 ECS witness for Issue #181: real floating rod.
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/World.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Static.hh>
// Gazebo Sim8 component declarations: GravityEnabled in Gravity.hh,
// WorldPose in Pose.hh, WorldLinearVelocity in LinearVelocity.hh.
#include <gz/sim/components/Gravity.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/sim/components/LinearVelocity.hh>
#include <gz/plugin/Register.hh>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <cmath>
namespace ch07_181 {
class RodTrace final : public gz::sim::System,
                       public gz::sim::ISystemPostUpdate {
 public:
 RodTrace() {
  const auto *n=std::getenv("CH07_181_ROD_ECS_CSV");
  out_.open(n?n:"/tmp/ch07_181_rod_ecs.csv",std::ios::out|std::ios::trunc);
  out_<<"sim_time_s,model_entity,link_entity,static_present,model_static,"
         "gravity_present,gravity_enabled,pose_present,x_m,y_m,z_m,"
         "velocity_present,vx_mps,vy_mps,vz_mps,local_velocity_present,"
         "world_gravity_component_present,world_gravity_z_mps2,"
         "model_pose_present,link_local_pose_present,"
         "resolved_world_x_m,resolved_world_y_m,resolved_world_z_m,"
         "derived_world_vz_mps\n";
  out_.flush();
  std::cerr << "CH07_181_ROD_ECS_PLUGIN_CONSTRUCTOR path="
            << (n?n:"/tmp/ch07_181_rod_ecs.csv")
            << " open=" << out_.good() << std::endl;
 }
 void PostUpdate(const gz::sim::UpdateInfo &info,
                 const gz::sim::EntityComponentManager &ecm) override {
  if(info.paused||!out_.good())return;
  const double t=std::chrono::duration<double>(info.simTime).count();
  if(t-last_<.01)return;
  last_=t;
  const auto m=ecm.EntityByComponents(gz::sim::components::Model(),
                                     gz::sim::components::Name("g04_grasp_cylinder"));
  const auto l=ecm.EntityByComponents(gz::sim::components::Link(),
                                     gz::sim::components::Name("cylinder_link"));
  if(m==gz::sim::kNullEntity||l==gz::sim::kNullEntity)return;
  const auto st=ecm.Component<gz::sim::components::Static>(m);
  const auto gr=ecm.Component<gz::sim::components::GravityEnabled>(l);
  const auto p=ecm.Component<gz::sim::components::WorldPose>(l);
  const auto v=ecm.Component<gz::sim::components::WorldLinearVelocity>(l);
  const auto local=ecm.Component<gz::sim::components::LinearVelocity>(l);
  const auto modelPose=ecm.Component<gz::sim::components::Pose>(m);
  const auto linkPose=ecm.Component<gz::sim::components::Pose>(l);
  // WorldPose and WorldLinearVelocity ECS components are not created by
  // default in this original Gazebo Sim8 world. Their absence is NOT
  // evidence of gravity disabled or velocity zero. The official
  // gz::sim::worldPose() computes native world pose from existing
  // non-mutated Pose + parent link components.
  const auto resolved=gz::sim::worldPose(l,ecm).Pos();
  const auto world=ecm.EntityByComponents(
    gz::sim::components::World(),
    gz::sim::components::Name("book_camera"));
  const auto gravity=(world==gz::sim::kNullEntity) ?
    nullptr : ecm.Component<gz::sim::components::Gravity>(world);
  const auto nan=std::numeric_limits<double>::quiet_NaN();
  const auto estimatedVZ=std::isfinite(previousWorldZ_) && t>previousWorldT_
       ? (resolved.Z()-previousWorldZ_)/(t-previousWorldT_) : nan;
  previousWorldZ_=resolved.Z();
  previousWorldT_=t;
  out_<<std::setprecision(15)<<t<<','<<m<<','<<l
      <<','<<(st!=nullptr)<<','<<(st?int(st->Data()):-1)
      <<','<<(gr!=nullptr)<<','<<(gr?int(gr->Data()):-1)
      <<','<<(p!=nullptr)
      <<','<<(p?p->Data().Pos().X():nan)
      <<','<<(p?p->Data().Pos().Y():nan)
      <<','<<(p?p->Data().Pos().Z():nan)
      <<','<<(v!=nullptr)
      <<','<<(v?v->Data().X():nan)
      <<','<<(v?v->Data().Y():nan)
      <<','<<(v?v->Data().Z():nan)
      <<','<<(local!=nullptr)
      <<','<<(gravity!=nullptr)
      <<','<<(gravity?gravity->Data().Z():nan)
      <<','<<(modelPose!=nullptr)
      <<','<<(linkPose!=nullptr)
      <<','<<resolved.X()<<','<<resolved.Y()<<','<<resolved.Z()
      <<','<<estimatedVZ<<'\n';
  if(++count_%100==0)out_.flush();
 }
 private:
 std::ofstream out_;
 double last_=-1.0;
 double previousWorldZ_=std::numeric_limits<double>::quiet_NaN();
 double previousWorldT_=-1.0;
 unsigned long count_=0;
};
}
GZ_ADD_PLUGIN(ch07_181::RodTrace,gz::sim::System,
              ch07_181::RodTrace::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(ch07_181::RodTrace,"ch07_181::RodTrace")
