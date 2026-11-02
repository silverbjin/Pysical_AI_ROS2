// SPDX-License-Identifier: Apache-2.0
// Ch13 independently derived energy/Jacobian model. No DART or ROS dependency.
#include <Eigen/Dense>
#include <Eigen/Geometry>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <ctime>
#include <cstdio>
#include <stdexcept>
#include <algorithm>
namespace {
using M=Eigen::MatrixXd;using V=Eigen::VectorXd;using V3=Eigen::Vector3d;using M3=Eigen::Matrix3d;using M4=Eigen::Matrix4d;
using R4=Eigen::Matrix<double,4,4,Eigen::RowMajor>;using R3=Eigen::Matrix<double,3,3,Eigen::RowMajor>;
double now(clockid_t c){timespec t{};if(clock_gettime(c,&t))throw std::runtime_error("clock");return t.tv_sec*1e9+t.tv_nsec;}
M3 skew(const V3 &p){M3 s;s<<0.,-p.z(),p.y(),p.z(),0.,-p.x(),-p.y(),p.x(),0.;return s;}
template<class T>T matrix(const nlohmann::json &v){T m;if(v.size()!=size_t(m.size()))throw std::invalid_argument("matrix size");for(int i=0;i<m.rows();++i)for(int j=0;j<m.cols();++j)m(i,j)=v.at(i*m.cols()+j).template get<double>();if(!m.allFinite())throw std::invalid_argument("nonfinite plan");return m;}
struct Node{int parent,q;std::string kind;M4 origin,inertial;V3 axis;double mass;M3 tensor;};
struct Plan{
 std::vector<Node> nodes;int nq,nd;V d,k,cap;std::vector<int>feet,legs;V radii;double total=0.;
 explicit Plan(const nlohmann::json&j):nq(j.at("names").size()),nd(nq+6),d(V::Zero(nd)),k(nq),cap(nq),feet(j.at("feet").get<std::vector<int>>()),legs(j.at("leg_indices").get<std::vector<int>>()),radii(4){
  if(nq<=0||nq>64||feet.size()!=4||legs.size()!=12)throw std::invalid_argument("model dimensions");
  for(int i=0;i<nq;++i){d(6+i)=j.at("damping").at(i);k(i)=j.at("gains").at(i);cap(i)=j.at("effort").at(i);if(!std::isfinite(d(6+i))||d(6+i)<0||!std::isfinite(k(i))||k(i)<=0||!std::isfinite(cap(i))||cap(i)<=0)throw std::invalid_argument("PD limits");}
  for(int i=0;i<4;++i){radii(i)=j.at("radii").at(i);if(!std::isfinite(radii(i))||radii(i)<=0)throw std::invalid_argument("sphere radius");}
  for(const auto&v:j.at("nodes")){Node n{v.at("parent"),v.at("q"),v.at("kind"),matrix<M4>(v.at("origin")),matrix<M4>(v.at("inertial")),matrix<V3>(v.at("axis")),v.at("mass"),matrix<M3>(v.at("tensor"))};
   if(n.parent>=int(nodes.size())||n.parent< -1||n.q< -1||n.q>=nq||!std::isfinite(n.mass)||n.mass<0)throw std::invalid_argument("node topology");
   if(n.kind!="fixed"&&n.kind!="revolute"&&n.kind!="continuous"&&n.kind!="prismatic")throw std::invalid_argument("joint type");
   if(n.q>=0){if(n.axis.norm()<1e-12)throw std::invalid_argument("joint axis");n.axis.normalize();}
   total+=n.mass;nodes.push_back(n);}
  for(int i:feet){if(i<0||i>=int(nodes.size()))throw std::invalid_argument("foot index");}
  for(int i:legs){if(i<0||i>=nq)throw std::invalid_argument("leg index");}
 }
 struct State{M mass,contact,mapped;V gravity;};
 State state(const V&q,const M4&body)const{
  std::vector<M4>frames(nodes.size());std::vector<V3>axes(nodes.size()),origins(nodes.size());
  for(size_t i=0;i<nodes.size();++i){const auto&n=nodes[i];M4 f=n.parent<0?body:frames[n.parent]*n.origin;
   if(n.q>=0){axes[i]=f.block<3,3>(0,0)*n.axis;origins[i]=f.block<3,1>(0,3);M4 motion=M4::Identity();
    if(n.kind=="prismatic")motion.block<3,1>(0,3)=n.axis*q(n.q);else motion.block<3,3>(0,0)=Eigen::AngleAxisd(q(n.q),n.axis).toRotationMatrix();f=f*motion;}
   frames[i]=f;}
  auto jac=[&](int link,const V3&p,M&v,M&w){v.setZero(3,nd);w.setZero(3,nd);v.block<3,3>(0,0).setIdentity();v.block<3,3>(0,3)=-skew(p-body.block<3,1>(0,3));w.block<3,3>(0,3).setIdentity();
   for(int a=link;a>=0;a=nodes[a].parent){const auto&n=nodes[a];if(n.q>=0){if(n.kind=="prismatic")v.col(6+n.q)=axes[a];else{v.col(6+n.q)=axes[a].cross(p-origins[a]);w.col(6+n.q)=axes[a];}}}};
  State s{M::Zero(nd,nd),M::Zero(12,nd),M(),V::Zero(nd)};M v,w;
  for(size_t i=0;i<nodes.size();++i){const auto&n=nodes[i];if(n.mass==0&&n.tensor.isZero(0.))continue;M4 f=frames[i]*n.inertial;jac(i,f.block<3,1>(0,3),v,w);M3 rot=f.block<3,3>(0,0);M3 inertia=rot*n.tensor*rot.transpose();
   s.mass.noalias()+=n.mass*v.transpose()*v+w.transpose()*inertia*w;s.gravity.noalias()+=n.mass*9.81*v.row(2).transpose();}
  for(int i=0;i<4;++i){V3 p=frames[feet[i]].block<3,1>(0,3)-radii(i)*V3::UnitZ();jac(feet[i],p,v,w);s.contact.middleRows<3>(3*i)=v;}
  Eigen::LDLT<M> ldlt(s.mass);if(ldlt.info()!=Eigen::Success||!ldlt.isPositive())throw std::invalid_argument("nonpositive inertia");
  s.mapped=s.contact.transpose()+.002*d.asDiagonal()*ldlt.solve(s.contact.transpose());return s;
 }
 M evaluate(const double*input,double&residual)const{
  Eigen::Map<const V>q(input,nq),cmd(input+nq,nq),force(input+2*nq+16,12);M4 body=Eigen::Map<const R4>(input+2*nq);
  if((body.row(3)-Eigen::RowVector4d(0,0,0,1)).norm()>1e-10||(body.block<3,3>(0,0).transpose()*body.block<3,3>(0,0)-M3::Identity()).norm()>1e-7)throw std::invalid_argument("rigid pose");
  State s=state(q,body);M grad=M::Zero(nd,nd);constexpr double eps=1e-6;
  // Translation invariance makes the first three derivatives exactly zero.
  auto equation=[&](const V&qv,const M4&pose)->V{State a=state(qv,pose);V u=V::Zero(nd);for(int i=0;i<nq;++i)u(6+i)=std::clamp(k(i)*(cmd(i)-qv(i)),-cap(i),cap(i));return u-a.gravity+a.mapped*force;};
  for(int i=3;i<nd;++i){V plus=q,minus=q;M4 bp=body,bm=body;if(i<6){V3 axis=V3::Zero();axis(i-3)=1.;bp.block<3,3>(0,0)=Eigen::AngleAxisd(eps,axis).toRotationMatrix()*body.block<3,3>(0,0);bm.block<3,3>(0,0)=Eigen::AngleAxisd(-eps,axis).toRotationMatrix()*body.block<3,3>(0,0);}else{plus(i-6)+=eps;minus(i-6)-=eps;}grad.col(i)=(equation(plus,bp)-equation(minus,bm))/(2*eps);}
  M a=M::Zero(nd+12,nd+12);a.topLeftCorner(nd,nd)=grad;a.topRightCorner(nd,12)=s.mapped;a.bottomLeftCorner(12,nd)=s.contact;
  M rhs=M::Zero(nd+12,12);for(int i=0;i<12;++i){int j=legs[i];double raw=k(j)*(cmd(j)-q(j));if(std::abs(raw-cap(j))<k(j)*eps||std::abs(raw+cap(j))<k(j)*eps)throw std::invalid_argument("nondifferentiable actuator boundary");if(std::abs(raw)<cap(j))rhs(6+j,i)=-k(j);}
  Eigen::FullPivLU<M> lu(a);lu.setThreshold(1e-11);if(!lu.isInvertible())throw std::invalid_argument("singular equilibrium");M solution=lu.solve(rhs);residual=(a*solution-rhs).cwiseAbs().maxCoeff();if(!solution.allFinite()||residual>1e-6)throw std::invalid_argument("equilibrium residual");return solution;
 }
};
}
extern "C" void* ch13_equilibrium_create(const char*text,char*error,size_t size){try{return new Plan(nlohmann::json::parse(text));}catch(const std::exception&e){if(error&&size)std::snprintf(error,size,"%s",e.what());return nullptr;}}
extern "C" void ch13_equilibrium_destroy(void*p){delete static_cast<Plan*>(p);}
extern "C" int ch13_equilibrium_evaluate(void*handle,const double*input,size_t count,double*output,size_t size,char*error,size_t error_size){try{
 if(!handle||!input||!output){throw std::invalid_argument("missing equilibrium buffers");}
 const auto&p=*static_cast<Plan*>(handle);if(count!=size_t(2*p.nq+28)||size!=size_t(144+p.nd*12+4))throw std::invalid_argument("equilibrium dimensions");for(size_t i=0;i<count;++i)if(!std::isfinite(input[i]))throw std::invalid_argument("nonfinite equilibrium input");
 double start=now(CLOCK_MONOTONIC),cpu=now(CLOCK_THREAD_CPUTIME_ID),residual=0.;M solution=p.evaluate(input,residual);double wall=now(CLOCK_MONOTONIC)-start;if(wall>10000000.)throw std::runtime_error("equilibrium time budget");
 for(int i=0;i<12;++i){for(int j=0;j<12;++j){output[12*i+j]=solution(p.nd+i,j);}}
 for(int i=0;i<p.nd;++i){for(int j=0;j<12;++j){output[144+12*i+j]=solution(i,j);}}
 output[size-4]=p.total;output[size-3]=residual;output[size-2]=wall;output[size-1]=now(CLOCK_THREAD_CPUTIME_ID)-cpu;return 0;
 }catch(const std::exception&e){if(error&&error_size)std::snprintf(error,error_size,"%s",e.what());return 1;}}
