// Ch13 standalone diagnostic; no robot controller or installed source changes.
#include <gz/sim/TestFixture.hh>
#include <gz/sim/Server.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Collision.hh>
#include <cmath>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace sim = gz::sim;
namespace c = gz::sim::components;
struct Row {size_t step; long long time, dt; double command, velocity, wrench, contact_z;};
int main(int argc, char **argv) {
  if (argc != 3) return 2;
  const std::string mode = argv[2];
  if (mode != "every_step" && mode != "control_period" && mode != "upper_stop" && mode != "contact_static") return 2;
  std::vector<Row> rows;
  size_t step=0, writes=0;
  sim::Entity joint=sim::kNullEntity;
  sim::Entity collision=sim::kNullEntity;
  bool run_ok=false;
  {
    sim::TestFixture fixture(argv[1]);
    fixture.OnPreUpdate([&](const sim::UpdateInfo &info, sim::EntityComponentManager &ecm) {
      if (joint==sim::kNullEntity) {
        joint=ecm.EntityByComponents(c::Joint(), c::Name("drive"));
        if (joint==sim::kNullEntity) throw std::runtime_error("drive absent");
        ecm.CreateComponent(joint,c::JointVelocity());
        ecm.CreateComponent(joint,c::JointTransmittedWrench());
        ecm.CreateComponent(joint,c::JointForceCmd({0.}));
        if (mode=="contact_static") {
          collision=ecm.EntityByComponents(c::Collision(),c::Name("tip"));
          if (collision==sim::kNullEntity) throw std::runtime_error("tip absent");
          ecm.CreateComponent(collision,c::ContactSensorData());
        }
      }
      if (info.paused) throw std::runtime_error("unexpected pause");
      if (step<10 || mode!="control_period" || (step-10)%5==0) {
        ecm.SetComponentData<c::JointForceCmd>(joint,{step<10?0.:1.});
        if (step>=10) ++writes;
      }
    }).OnPostUpdate([&](const sim::UpdateInfo &info, const sim::EntityComponentManager &ecm) {
      const auto *v=ecm.Component<c::JointVelocity>(joint);
      const auto *w=ecm.Component<c::JointTransmittedWrench>(joint);
      const auto *f=ecm.Component<c::JointForceCmd>(joint);
      if (!v || v->Data().size()!=1 || !w || !f || f->Data().size()!=1)
        throw std::runtime_error("incomplete physics sample");
      double contact_z=0.;
      if (collision!=sim::kNullEntity) {
        const auto *contacts=ecm.Component<c::ContactSensorData>(collision);
        if (!contacts) throw std::runtime_error("contact data absent");
        for (const auto &pair:contacts->Data().contact())
          for (const auto &wrench:pair.wrench())
            contact_z+=pair.collision1().id()==collision?wrench.body_1_wrench().force().z():wrench.body_2_wrench().force().z();
      }
      rows.push_back({step,std::chrono::duration_cast<std::chrono::nanoseconds>(info.simTime).count(),
        std::chrono::duration_cast<std::chrono::nanoseconds>(info.dt).count(),
        f->Data()[0],v->Data()[0],w->Data().torque().y(),contact_z});
      ++step;
    }).Finalize();
    run_ok=fixture.Server()->Run(true,mode=="contact_static"?1010:110,false);
    fixture.Server()->Stop();
  } // synchronous finite run + server destruction before reporting closure
  std::cout << std::setprecision(17);
  std::cout << "step,time_ns,dt_ns,post_command_nm,velocity_rad_s,wrench_y_nm,contact_z_n\n";
  for (const auto &r:rows) std::cout<<r.step<<','<<r.time<<','<<r.dt<<','<<r.command<<','<<r.velocity<<','<<r.wrench<<','<<r.contact_z<<'\n';
  const size_t count=mode=="contact_static"?1010:110;
  const double actual=rows.size()==count ? rows.back().velocity-rows[9].velocity : -1.;
  const double expected=(mode=="upper_stop" || mode=="contact_static") ? 0. : static_cast<double>(writes)*1.*.002/.1;
  bool valid=run_ok && rows.size()==count && std::abs(actual-expected)<(mode=="contact_static"?1e-6:1e-9);
  for (const auto &r:rows) valid=valid && r.dt==2000000 && std::isfinite(r.velocity);
  std::cerr << "mode="<<mode<<" run_ok="<<run_ok<<" samples="<<rows.size()<<" writes="<<writes
            <<" expected_delta_qd="<<expected<<" actual_delta_qd="<<actual
            <<" server_destroyed=true analytic_check="<<(valid?"PASS":"FAIL")<<'\n';
  return valid?0:1;
}
