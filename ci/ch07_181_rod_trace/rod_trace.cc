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
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/plugin/Register.hh>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <cmath>
#include <string>
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
  // Separate read-only, same-Gazebo-PostUpdate-frame contact/ECS receipt.
  const auto *c=std::getenv("CH07_181_SYNC_CONTACT_CSV");
  sync_.open(c?c:"/tmp/ch07_181_ecs_contact_sync.csv",
             std::ios::out|std::ios::trunc);
  sync_<<"sim_time_s,rod_x,rod_y,rod_z,rod_qx,rod_qy,rod_qz,rod_qw,"
          "f1_link_x,f1_link_y,f1_link_z,f1_qx,f1_qy,f1_qz,f1_qw,"
          "f1_collision_present,f1_contact_ecs_present,f1_rod_pair_count,"
          "f1_latest_contact_stamp_s,"
          "f2_link_x,f2_link_y,f2_link_z,f2_qx,f2_qy,f2_qz,f2_qw,"
          "f2_collision_present,f2_contact_ecs_present,f2_rod_pair_count,"
          "f2_latest_contact_stamp_s\n";
  sync_.flush();
  std::cerr<<"CH07_181_ECS_CONTACT_SYNC_CONSTRUCTOR path="
           <<(c?c:"/tmp/ch07_181_ecs_contact_sync.csv")
           <<" open="<<sync_.good()<<std::endl;
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
  const auto rodWorld=gz::sim::worldPose(l,ecm);
  const auto resolved=rodWorld.Pos();
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
  if(sync_.good()) {
    const auto q=rodWorld.Rot();
    sync_<<std::setprecision(15)<<t<<','<<resolved.X()<<','<<resolved.Y()
         <<','<<resolved.Z()<<','<<q.X()<<','<<q.Y()<<','<<q.Z()<<','<<q.W();
    LogFinger(ecm,"finger1","finger1_collision");
    LogFinger(ecm,"finger2","finger2_collision");
    sync_<<'\n';
  }
  if(++count_%100==0) { out_.flush();sync_.flush(); }
 }
 private:
 // READ ONLY: all Gazebo ECS components and native collision-pair stamps
 // are sampled in the same PostUpdate call; neither ECM nor physics is
 // changed. A missing component is recorded as unavailable, NEVER zero force.
 void LogFinger(const gz::sim::EntityComponentManager &ecm,
                const std::string &name,const std::string &collisionName) {
   const auto link=ecm.EntityByComponents(
       gz::sim::components::Link(),gz::sim::components::Name(name));
   const auto collision=ecm.EntityByComponents(
       gz::sim::components::Collision(),
       gz::sim::components::Name(collisionName));
   const auto nan=std::numeric_limits<double>::quiet_NaN();
   if(link==gz::sim::kNullEntity) {
     for(int i=0;i<7;++i)sync_<<','<<nan;
   } else {
     const auto pose=gz::sim::worldPose(link,ecm);
     const auto p=pose.Pos();const auto q=pose.Rot();
     sync_<<','<<p.X()<<','<<p.Y()<<','<<p.Z()
          <<','<<q.X()<<','<<q.Y()<<','<<q.Z()<<','<<q.W();
   }
   const auto data=(collision==gz::sim::kNullEntity) ? nullptr :
       ecm.Component<gz::sim::components::ContactSensorData>(collision);
   int matched=0;double lastStamp=nan;
   if(data) {
     const auto &all=data->Data();
     for(int i=0;i<all.contact_size();++i) {
       const auto &contact=all.contact(i);
       const auto &a=contact.collision1().name();
       const auto &b=contact.collision2().name();
       if((a.find("g04_grasp_cylinder")!=std::string::npos ||
           b.find("g04_grasp_cylinder")!=std::string::npos) &&
          (a.find(collisionName)!=std::string::npos ||
           b.find(collisionName)!=std::string::npos)) {
          ++matched;
          const auto &stamp=contact.header().stamp();
          const double cstamp=stamp.sec()+stamp.nsec()*1e-9;
          if(!std::isfinite(lastStamp) || cstamp>lastStamp)lastStamp=cstamp;
       }
     }
   }
   sync_<<','<<(collision!=gz::sim::kNullEntity)
        <<','<<(data!=nullptr)<<','<<(data?matched:-1)
        <<','<<lastStamp;
 }
 std::ofstream out_;
 std::ofstream sync_;
 double last_=-1.0;
 double previousWorldZ_=std::numeric_limits<double>::quiet_NaN();
 double previousWorldT_=-1.0;
 unsigned long count_=0;
};
}
GZ_ADD_PLUGIN(ch07_181::RodTrace,gz::sim::System,
              ch07_181::RodTrace::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(ch07_181::RodTrace,"ch07_181::RodTrace")
