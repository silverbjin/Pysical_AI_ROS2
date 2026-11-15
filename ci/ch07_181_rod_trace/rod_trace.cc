// READ-ONLY Gazebo Sim8 ECS witness for Issue #181: real floating rod.
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Static.hh>
#include <gz/sim/components/GravityEnabled.hh>
#include <gz/sim/components/WorldPose.hh>
#include <gz/sim/components/WorldLinearVelocity.hh>
#include <gz/sim/components/LinearVelocity.hh>
#include <gz/plugin/Register.hh>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
namespace ch07_181 {
class RodTrace final : public gz::sim::System,
                       public gz::sim::ISystemPostUpdate {
 public:
 RodTrace() {
  const auto *n=std::getenv("CH07_181_ROD_ECS_CSV");
  out_.open(n?n:"/tmp/ch07_181_rod_ecs.csv",std::ios::out|std::ios::trunc);
  out_<<"sim_time_s,model_entity,link_entity,static_present,model_static,"
         "gravity_present,gravity_enabled,pose_present,x_m,y_m,z_m,"
         "velocity_present,vx_mps,vy_mps,vz_mps,local_velocity_present\n";
  out_.flush();
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
  const auto nan=std::numeric_limits<double>::quiet_NaN();
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
      <<','<<(local!=nullptr)<<'\n';
  if(++count_%100==0)out_.flush();
 }
 private:
 std::ofstream out_;
 double last_=-1.0;
 unsigned long count_=0;
};
}
GZ_ADD_PLUGIN(ch07_181::RodTrace,gz::sim::System,
              ch07_181::RodTrace::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(ch07_181::RodTrace,"ch07_181::RodTrace")
