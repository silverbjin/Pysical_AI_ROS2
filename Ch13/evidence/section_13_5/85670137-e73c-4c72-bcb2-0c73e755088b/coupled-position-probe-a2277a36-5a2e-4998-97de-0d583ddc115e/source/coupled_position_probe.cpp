// Standalone four-contact diagnostic. Not the Ch13 robot, G1, C1 or G2.
#include <gz/sim/TestFixture.hh>
#include <gz/sim/Server.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <nlohmann/json.hpp>
#include <array>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <stdexcept>
namespace sim=gz::sim;
namespace c=sim::components;
using A=std::array<double,4>;
using Json=nlohmann::json;
struct Mean {
 size_t count=0;A force{},squared{},position{},velocity{},raw{};
 void add(const A &f,const A &q,const A &v,const A &u) {
  ++count;for(size_t i=0;i<4;++i) {force[i]+=f[i];squared[i]+=f[i]*f[i];position[i]+=q[i];velocity[i]+=v[i];raw[i]+=u[i];}
 }
 Json finish(const A &target,size_t condition)const {
  if(count!=200) throw std::runtime_error("fixed summary sample count");
  A f{},sd{},q{},v{},u{};
  for(size_t i=0;i<4;++i) {
   f[i]=force[i]/count;sd[i]=std::sqrt(std::max(0.,squared[i]/count-f[i]*f[i]));
   q[i]=position[i]/count;v[i]=velocity[i]/count;u[i]=raw[i]/count;
  }
  return {{"condition",condition},{"samples",count},{"target_m",target},{"mean_force_z_n",f},
   {"force_z_std_n",sd},{"mean_position_m",q},{"mean_velocity_mps",v},{"mean_raw_pd_force_n",u}};
 }
};
int main(int argc,char **argv) {
 if(argc!=2) return 2;
 constexpr size_t warmup=3000,per_case=2000,cases=9,total=warmup+per_case*cases;
 const std::array<std::string,4> names{"fr","fl","rr","rl"};
 std::array<sim::Entity,4> joints{},collisions{};A command{},last{},raw{};Mean mean;
 bool configured=false,ok=false;size_t step=0;Json reports=Json::array();
 {
  sim::TestFixture fixture(argv[1]);
  fixture.OnPreUpdate([&](const sim::UpdateInfo &info,sim::EntityComponentManager &ecm) {
   if(info.paused || info.dt!=std::chrono::milliseconds(2)) throw std::runtime_error("fixed unpaused2ms required");
   if(!configured) {
    for(size_t i=0;i<4;++i) {
     joints[i]=ecm.EntityByComponents(c::Joint(),c::Name(names[i]+"_slide"));
     collisions[i]=ecm.EntityByComponents(c::Collision(),c::Name(names[i]+"_tip"));
     if(!joints[i] || !collisions[i]) throw std::runtime_error("fixture joint/collision missing");
     ecm.CreateComponent(joints[i],c::JointPosition());ecm.CreateComponent(joints[i],c::JointVelocity());
     ecm.CreateComponent(joints[i],c::JointForceCmd({0.}));
     ecm.CreateComponent(collisions[i],c::ContactSensorData());
    }
    configured=true;
   }
   size_t condition=step<warmup?0:(step-warmup)/per_case;
   size_t local=step<warmup?0:(step-warmup)%per_case;
   if(step>=warmup && local==0) {last=command;mean=Mean();}
   A target{};
   if(condition>0) target[(condition-1)/2]=condition%2?0.0001:-0.0001;
   double weight=step<warmup?1.:std::min(1.,static_cast<double>(local+1)/50.);
   for(size_t i=0;i<4;++i) {
    command[i]=last[i]*(1.-weight)+target[i]*weight;
    const auto *q=ecm.Component<c::JointPosition>(joints[i]);
    raw[i]=(!q || q->Data().empty())?0.:750.*(command[i]-q->Data()[0]);
    if(!std::isfinite(raw[i])) throw std::runtime_error("nonfinite PD");
    ecm.SetComponentData<c::JointForceCmd>(joints[i],{std::clamp(raw[i],-30.,30.)});
   }
  }).OnPostUpdate([&](const sim::UpdateInfo &,const sim::EntityComponentManager &ecm) {
   if(step>=warmup && (step-warmup)%per_case>=per_case-200) {
    A f{},q{},v{};
    for(size_t i=0;i<4;++i) {
     const auto *contacts=ecm.Component<c::ContactSensorData>(collisions[i]);
     const auto *position=ecm.Component<c::JointPosition>(joints[i]);
     const auto *velocity=ecm.Component<c::JointVelocity>(joints[i]);
     if(!contacts || !position || position->Data().size()!=1 || !velocity || velocity->Data().size()!=1)
      throw std::runtime_error("missing actual measurement");
     q[i]=position->Data()[0];v[i]=velocity->Data()[0];
     for(const auto &pair:contacts->Data().contact()) for(const auto &w:pair.wrench())
      f[i]+=pair.collision1().id()==collisions[i]?w.body_1_wrench().force().z():w.body_2_wrench().force().z();
     if(!std::isfinite(f[i]) || f[i]<=0. || std::abs(raw[i])>=30.) throw std::runtime_error("lost support or force saturation");
    }
    mean.add(f,q,v,raw);
    if((step-warmup)%per_case==per_case-1) reports.push_back(mean.finish(command,(step-warmup)/per_case));
   }
   ++step;
  }).Finalize();
  ok=fixture.Server()->Run(true,total,false);fixture.Server()->Stop();
 }
 std::cout<<Json({{"scope","four_prismatic_supports_position_force_diagnostic_not_robot_acceptance"},
  {"server_run_ok",ok},{"server_destroyed",true},{"steps",step},{"physics_dt_s",.002},
  {"kp_n_per_m",750.},{"damping_ns_per_m",10.954451150103322},{"foot_mass_kg",.1},
  {"trunk_mass_kg",1.},{"force_cap_n",30.},{"input_delta_m",.0001},
  {"order",names},{"conditions",reports}}).dump(2)<<'\n';
 return ok && step==total && reports.size()==cases?0:1;
}
