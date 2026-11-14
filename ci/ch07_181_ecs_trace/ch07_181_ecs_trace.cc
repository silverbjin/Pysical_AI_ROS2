// Ch07 Issue #181: READ-ONLY Gazebo ECS joint command/physics trace.
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/Name.hh>
#include <gz/plugin/Register.hh>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <mutex>
#include <string>
#include <vector>
namespace ch07_181 {
class JointEcsTrace final: public gz::sim::System,
  public gz::sim::ISystemPreUpdate, public gz::sim::ISystemPostUpdate {
public:
 JointEcsTrace() {
  const char *filename=std::getenv("CH07_181_ECS_CSV");
  out_.open(filename?filename:"/tmp/ch07_181_ecs_trace.csv",std::ios::out|std::ios::trunc);
  out_ << "sim_time_s,phase,joint_entity,velocity_cmd_present,velocity_cmd_size,"
          "velocity_cmd_mps,position_present,position_m,velocity_present,"
          "velocity_mps,force_cmd_present,force_cmd_n\n";
  out_.flush();
 }
 void PreUpdate(const gz::sim::UpdateInfo &info,
                gz::sim::EntityComponentManager &ecm) override {
   Record(info,ecm,"pre",lastPre_);
 }
 void PostUpdate(const gz::sim::UpdateInfo &info,
                 const gz::sim::EntityComponentManager &ecm) override {
   Record(info,ecm,"post",lastPost_);
 }
private:
 void Record(const gz::sim::UpdateInfo &info,
             const gz::sim::EntityComponentManager &ecm,
             const char *phase,double &last) {
  if(info.paused) return;
  const double now=std::chrono::duration<double>(info.simTime).count();
  if(now-last<0.004) return;
  last=now;
  // Original Gazebo robot is spawned AFTER the world starts; never create one.
  const auto entity=ecm.EntityByComponents(
    gz::sim::components::Joint(),gz::sim::components::Name("joint_finger2"));
  if(entity==gz::sim::kNullEntity) return;
  const auto cmd=ecm.Component<gz::sim::components::JointVelocityCmd>(entity);
  const auto pos=ecm.Component<gz::sim::components::JointPosition>(entity);
  const auto vel=ecm.Component<gz::sim::components::JointVelocity>(entity);
  const auto force=ecm.Component<gz::sim::components::JointForceCmd>(entity);
  const auto scalar=[](const std::vector<double> &v) {
    return v.empty()?std::numeric_limits<double>::quiet_NaN():v[0];
  };
  std::lock_guard<std::mutex> lock(mutex_);
  if(!out_.good()) return;
  out_<<std::setprecision(15)<<now<<','<<phase<<','<<entity
      <<','<<(cmd!=nullptr)<<','<<(cmd?cmd->Data().size():0)
      <<','<<(cmd?scalar(cmd->Data()):std::numeric_limits<double>::quiet_NaN())
      <<','<<(pos!=nullptr)
      <<','<<(pos?scalar(pos->Data()):std::numeric_limits<double>::quiet_NaN())
      <<','<<(vel!=nullptr)
      <<','<<(vel?scalar(vel->Data()):std::numeric_limits<double>::quiet_NaN())
      <<','<<(force!=nullptr)
      <<','<<(force?scalar(force->Data()):std::numeric_limits<double>::quiet_NaN())
      <<'\n';
  if(++lines_%250==0)out_.flush();
 }
 std::ofstream out_; std::mutex mutex_;
 double lastPre_=-1.0,lastPost_=-1.0;
 unsigned long lines_=0;
};
}
GZ_ADD_PLUGIN(ch07_181::JointEcsTrace,gz::sim::System,
 ch07_181::JointEcsTrace::ISystemPreUpdate,
 ch07_181::JointEcsTrace::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(ch07_181::JointEcsTrace,"ch07_181::JointEcsTrace")
