// Issue #181: BOTH finger joints, READ-ONLY pre/post-physics native ECS.
// Proven API/priority pattern reused from Draft PR #187, not a new controller.
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointForceCmd.hh>
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
class FingerEcsTrace final : public gz::sim::System,
  public gz::sim::ISystemConfigurePriority,
  public gz::sim::ISystemPreUpdate,
  public gz::sim::ISystemPostUpdate {
 public:
  gz::sim::System::PriorityType ConfigurePriority() override { return 100; }
  FingerEcsTrace() {
    const char *filename=std::getenv("CH07_181_FINGER_ECS_CSV");
    out_.open(filename?filename:"/tmp/ch07_181_finger_ecs_trace.csv",
              std::ios::out|std::ios::trunc);
    out_<<"sim_time_s,phase,joint_name,joint_entity,"
           "velocity_cmd_present,velocity_cmd_size,velocity_cmd_mps,"
           "position_present,position_m,velocity_present,velocity_mps,"
           "force_cmd_present,force_cmd_n\n";
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
    if(info.paused)return;
    const double now=std::chrono::duration<double>(info.simTime).count();
    if(now-last<.004)return;
    last=now;
    const auto scalar=[](const std::vector<double> &v) {
      return v.empty()?std::numeric_limits<double>::quiet_NaN():v[0];
    };
    std::lock_guard<std::mutex> lock(mutex_);
    if(!out_.good())return;
    for(const char *name : {"joint_finger1","joint_finger2"}) {
      const auto entity=ecm.EntityByComponents(
        gz::sim::components::Joint(),gz::sim::components::Name(name));
      if(entity==gz::sim::kNullEntity)continue;
      const auto cmd=ecm.Component<gz::sim::components::JointVelocityCmd>(entity);
      const auto pos=ecm.Component<gz::sim::components::JointPosition>(entity);
      const auto vel=ecm.Component<gz::sim::components::JointVelocity>(entity);
      const auto force=ecm.Component<gz::sim::components::JointForceCmd>(entity);
      out_<<std::setprecision(15)<<now<<','<<phase<<','<<name<<','<<entity
          <<','<<(cmd!=nullptr)<<','<<(cmd?cmd->Data().size():0)
          <<','<<(cmd?scalar(cmd->Data()):std::numeric_limits<double>::quiet_NaN())
          <<','<<(pos!=nullptr)
          <<','<<(pos?scalar(pos->Data()):std::numeric_limits<double>::quiet_NaN())
          <<','<<(vel!=nullptr)
          <<','<<(vel?scalar(vel->Data()):std::numeric_limits<double>::quiet_NaN())
          <<','<<(force!=nullptr)
          <<','<<(force?scalar(force->Data()):std::numeric_limits<double>::quiet_NaN())
          <<'\n';
    }
    if(++lines_%25==0)out_.flush();
  }
  std::ofstream out_;std::mutex mutex_;
  double lastPre_=-1.,lastPost_=-1.;
  unsigned long lines_=0;
};
}
GZ_ADD_PLUGIN(ch07_181::FingerEcsTrace,gz::sim::System,
  ch07_181::FingerEcsTrace::ISystemConfigurePriority,
  ch07_181::FingerEcsTrace::ISystemPreUpdate,
  ch07_181::FingerEcsTrace::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(ch07_181::FingerEcsTrace,"ch07_181::FingerEcsTrace")
