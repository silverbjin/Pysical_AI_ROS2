// Offline DART API oracle. No world step, installed mutation, controller or command.
#include <dart/utils/urdf/DartLoader.hpp>
#include <dart/dynamics/Skeleton.hpp>
#include <dart/dynamics/BodyNode.hpp>
#include <dart/dynamics/FreeJoint.hpp>
#include <dart/dynamics/DegreeOfFreedom.hpp>
#include <Eigen/Cholesky>
#include <Eigen/Eigenvalues>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
using Json=nlohmann::json;
int main(int argc,char **argv) {
 if(argc!=2) return 2;
 std::ifstream in(argv[1]);Json f;in>>f;
 // Gazebo's massless optical frames must not receive DartLoader's default
 // 1 kg / unit-inertia bodies. The robot URDF itself remains unchanged.
 dart::dynamics::Inertia massless;
 massless.setMass(0.);massless.setMoment(Eigen::Matrix3d::Zero());
 dart::utils::DartLoader loader(dart::utils::DartLoader::Options(nullptr,
   dart::utils::DartLoader::RootJointType::FLOATING,massless));
 auto s=loader.parseSkeletonString(f.at("urdf").get<std::string>(),".");
 if(!s) throw std::runtime_error("URDF parsing failed");
 if(std::abs(s->getMass()-15.2101)>1e-8) throw std::runtime_error("original mass mismatch");
 auto &a=f.at("args");
 for(auto it=a.at("joints").begin();it!=a.at("joints").end();++it) {
  auto *j=s->getJoint(it.key());
  if(!j || j->getNumDofs()!=1) throw std::runtime_error("scalar joint missing");
  j->setPosition(0,it.value().get<double>());
 }
 Eigen::Isometry3d pose=Eigen::Isometry3d::Identity();
 for(int r=0;r<4;++r) for(int c=0;c<4;++c) pose.matrix()(r,c)=a.at("body_pose").at(r).at(c).get<double>();
 dart::dynamics::FreeJoint::setTransformOf(s->getRootBodyNode(),pose);
 s->setGravity(Eigen::Vector3d(0,0,-9.81));
 const Eigen::MatrixXd mass=s->getMassMatrix();
 const Eigen::VectorXd gravity=s->getGravityForces();
 Eigen::VectorXd contact=Eigen::VectorXd::Zero(s->getNumDofs());
 for(const auto &name: {"fr_foot","fl_foot","rr_foot","rl_foot"}) {
  auto *body=s->getBodyNode(name);
  if(!body) throw std::runtime_error("foot body missing");
  Eigen::Vector3d point,force;
  for(int k=0;k<3;++k) {point(k)=a.at("points").at(name).at(k);force(k)=a.at("forces_world").at(name).at(k);}
  const Eigen::Vector3d local=body->getWorldTransform().inverse()*point;
  contact+=s->getLinearJacobian(body,local,dart::dynamics::Frame::World()).transpose()*force;
 }
 const auto llt=mass.llt();
 if(llt.info()!=Eigen::Success) throw std::runtime_error("mass not SPD");
 const Eigen::VectorXd inverse_contact=llt.solve(contact);
 Json rows=Json::array();
 for(const auto &prefix:{"fr","fl","rr","rl"}) for(const auto &part:{"hip","thigh","calf"}) {
  const std::string name=std::string(prefix)+"_"+part+"_joint";
  auto *j=s->getJoint(name);const auto index=j->getDof(0)->getIndexInSkeleton();
  const double damping=j->getDampingCoefficient(0);
  const double stat=gravity(index)-contact(index),correction=-.002*damping*inverse_contact(index);
  rows.push_back({{"joint",name},{"damping",damping},{"gravity_nm",gravity(index)},
   {"contact_generalized_nm",contact(index)},{"continuous_static_nm",stat},
   {"implicit_constraint_correction_nm",correction},{"predicted_command_at_zero_velocity_nm",stat+correction}});
 }
 const Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> eigen(mass);
 std::cout<<Json({{"scope","offline_zero_velocity_contact_impulse_hypothesis_not_closed_loop_acceptance"},
  {"mass_kg",s->getMass()},{"dofs",s->getNumDofs()},{"mass_eigen_min",eigen.eigenvalues().minCoeff()},
  {"solve_residual",(mass*inverse_contact-contact).lpNorm<Eigen::Infinity>()},
  {"formula","tau = gravity - J^T F - h D M^-1 J^T F at v=0, a_net=0; diagnostic hypothesis"},
  {"rows",rows}}).dump(2)<<'\n';
}
