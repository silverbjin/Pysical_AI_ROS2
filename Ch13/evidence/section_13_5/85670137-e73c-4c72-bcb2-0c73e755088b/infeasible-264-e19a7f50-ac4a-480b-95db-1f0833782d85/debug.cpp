#include <fstream>
// SPDX-License-Identifier: Apache-2.0
// Ch13 spatial spring/QP arithmetic. QPMAD headers retain upstream notices.
// No ROS, worker, measured cache, reference integrator or command authority.
#include <qpmad/solver.h>
#include "integrated_robot_navigation_sensors/box_presolve.hpp"
#include "integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp"
#include "integrated_robot_navigation_sensors/inverse_remainder.hpp"
#include <Eigen/LU>
#include <nlohmann/json.hpp>
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <ctime>
#include <limits>
#include <stdexcept>

namespace {
using M=Eigen::MatrixXd;using V=Eigen::VectorXd;using V3=Eigen::Vector3d;using M3=Eigen::Matrix3d;
using R3=Eigen::Matrix<double,3,3,Eigen::RowMajor>;
using R4=Eigen::Matrix<double,4,4,Eigen::RowMajor>;
using R43=Eigen::Matrix<double,4,3,Eigen::RowMajor>;
using R42=Eigen::Matrix<double,4,2,Eigen::RowMajor>;
double ns(clockid_t id) {timespec t{};if(clock_gettime(id,&t)) {throw std::runtime_error("native clock unavailable");}return double(t.tv_sec)*1e9+t.tv_nsec;}
template<int N> Eigen::Matrix<double,N,1> array(const nlohmann::json & j) {
  if(!j.is_array() || j.size()!=N) {throw std::invalid_argument("XYZ plan dimensions");}
  Eigen::Matrix<double,N,1> out;
  for(int i=0;i<N;++i) {out(i)=j.at(i).get<double>();if(!std::isfinite(out(i))) {throw std::invalid_argument("nonfinite XYZ plan");}}return out;
}
M3 skew(const V3 & p) {M3 r;r<<0.,-p.z(),p.y(),p.z(),0.,-p.x(),-p.y(),p.x(),0.;return r;}
struct Leg {
  V3 hip;double offset,upper,lower;
  explicit Leg(const nlohmann::json & j):hip(array<3>(j.at("hip"))),offset(j.at("offset").get<double>()),upper(j.at("upper").get<double>()),lower(j.at("lower").get<double>()) {
    if(!std::isfinite(offset) || !std::isfinite(upper) || !std::isfinite(lower) || upper<=0. || lower<=0.) {throw std::invalid_argument("XYZ leg geometry");}
  }
  V3 command_point(const V3 & q) const {
    const double c=std::cos(q(0)),s=std::sin(q(0));
    const double x=-upper*std::sin(q(1))-lower*std::sin(q(1)+q(2));
    const double z=-upper*std::cos(q(1))-lower*std::cos(q(1)+q(2));
    return hip+V3(x,offset*c-z*s,offset*s+z*c);
  }
  M3 command_jacobian(const V3 & q) const {
    double c=std::cos(q(0)),s=std::sin(q(0));V3 shoulder=hip+V3(0.,offset*c,offset*s);
    V3 knee=shoulder+V3(-upper*std::sin(q(1)),upper*std::cos(q(1))*s,-upper*std::cos(q(1))*c);
    double x=-upper*std::sin(q(1))-lower*std::sin(q(1)+q(2)),z=-upper*std::cos(q(1))-lower*std::cos(q(1)+q(2));
    V3 point=hip+V3(x,offset*c-z*s,offset*s+z*c),a=point-hip,b=point-shoulder,d=point-knee;
    M3 j;j<<0.,c*b.z()-s*b.y(),c*d.z()-s*d.y(),-a.z(),s*b.x(),s*d.x(),a.y(),-c*b.x(),-c*d.x();return j;
  }
};
struct ServoLinearization {M3 displacement;V3 bias;double radius,remainder;};
ServoLinearization servo_linearization(const Leg & leg,const V3 & command,
  const R4 & reference,const V3 & world_origin,double unit) {
  const M3 rotation=reference.block<3,3>(0,0);
  if(rotation.determinant()==0.) {throw std::invalid_argument("singular servo reference");}
  const M3 inverse=rotation.partialPivLu().solve(M3::Identity());
  const V3 local=inverse*(world_origin-reference.block<3,1>(0,3));
  const V3 point=leg.command_point(command),error=local-point;
  const double rounding=64.*std::numeric_limits<double>::epsilon()*(1.+local.norm()+point.norm());
  const double distance=error.norm()+inverse.norm()*unit+rounding;
  const auto bound=integrated_robot_navigation_sensors::inverse_remainder(
    leg.command_jacobian(command),
    integrated_robot_navigation_sensors::leg_forward_hessian_bound(leg.offset,leg.upper,leg.lower),distance);
  return {bound.inverse*inverse*unit,bound.inverse*error,bound.radius,
    bound.joint_remainder+bound.inverse_norm_bound*rounding};
}
struct Plan {
  V gains,effort,physical;std::array<Leg,4> legs;double cap,speed,min_force;bool terminal_force;qpmad::Solver solver;
  explicit Plan(const nlohmann::json & j):gains(array<12>(j.at("gains"))),effort(array<12>(j.at("effort"))),physical(array<24>(j.at("physical"))),
    legs{Leg(j.at("legs").at(0)),Leg(j.at("legs").at(1)),Leg(j.at("legs").at(2)),Leg(j.at("legs").at(3))},
    cap(j.at("cap").get<double>()),speed(j.at("speed").get<double>()),min_force(j.at("min_force").get<double>()),
    terminal_force(j.value("force_objective",std::string("rate_1_per_s"))=="bounded_terminal_force") {
    const auto objective=j.value("force_objective",std::string("rate_1_per_s"));
    if(objective!="rate_1_per_s" && objective!="bounded_terminal_force") {throw std::invalid_argument("unknown XYZ force objective");}
    if((gains.array()<=0.).any() || (effort.array()<=0.).any() || !std::isfinite(cap) || cap<=0.
      || !std::isfinite(speed) || speed<=0. || !std::isfinite(min_force) || min_force<0.) {throw std::invalid_argument("XYZ positive limits required");}
    for(int i=0;i<12;++i) {if(physical(2*i)>physical(2*i+1)) {throw std::invalid_argument("XYZ physical bounds");}}
    solver.reserve(12,12,132);
  }
};
qpmad::SolverParameters parameters() {qpmad::SolverParameters p;p.max_iter_=32;p.tolerance_=1e-12;p.hessian_type_=qpmad::SolverParameters::HESSIAN_LOWER_TRIANGULAR;return p;}
bool affine(const R4 & p) {return (p.row(3)-Eigen::RowVector4d(0.,0.,0.,1.)).cwiseAbs().maxCoeff()<=1e-10;}
}
extern "C" int ch13_xyz_abi_version() {return 1;}
extern "C" void * ch13_xyz_create(const char * text,char * error,size_t size) {
  try {if(!text) {throw std::invalid_argument("XYZ plan missing");}return new Plan(nlohmann::json::parse(text));}
  catch(const std::exception & e) {if(error && size) {std::snprintf(error,size,"%s",e.what());}return nullptr;}
}
extern "C" void ch13_xyz_destroy(void * handle) {delete static_cast<Plan *>(handle);}
extern "C" int ch13_xyz_prepare(void * handle,char * error,size_t size) {
  try {
    if(!handle) {throw std::invalid_argument("XYZ plan missing");}auto & p=*static_cast<Plan *>(handle);
    M h=M::Identity(12,12),a=M::Zero(132,12);V x=V::Zero(12),g=V::Ones(12),lo=V::Constant(12,-.1),hi=V::Constant(12,.1);
    V alb=V::Constant(132,-std::numeric_limits<double>::infinity()),aub=V::Ones(132);
    auto status=p.solver.solve(x,h,g,lo,hi,a,alb,aub,parameters());
    if(status!=qpmad::Solver::OK || (x.array()+.1).abs().maxCoeff()>1e-9) {throw std::runtime_error("XYZ solver preparation failed");}return 0;
  } catch(const std::exception & e) {if(error && size) {std::snprintf(error,size,"%s",e.what());}return 1;}
}
extern "C" int ch13_xyz_evaluate(void * handle,const double * input,size_t count,int selected,
  double * output,size_t output_size,double * timings,size_t timing_size,char * error,size_t error_size) {
  if(!handle || !input || !output || !timings || count!=175 || output_size!=208 || timing_size!=8 || selected<0 || selected>3) {return 1;}
  std::fill(timings,timings+8,0.);
  try {
    const double start=ns(CLOCK_MONOTONIC),cpu=ns(CLOCK_THREAD_CPUTIME_ID);
    auto mark=[&](int index) {timings[2*index]=ns(CLOCK_MONOTONIC)-start;timings[2*index+1]=ns(CLOCK_THREAD_CPUTIME_ID)-cpu;
      if(timings[2*index]>10000000.) {throw std::runtime_error("native XYZ time budget");}};
    for(size_t i=0;i<count;++i) {if(!std::isfinite(input[i])) {throw std::invalid_argument("nonfinite XYZ input");}}
    auto & p=*static_cast<Plan *>(handle);Eigen::Map<const V> q(input,12),command(input+12,12),gravity(input+160,12);
    Eigen::Map<const R4> body(input+24),reference(input+40);
    Eigen::Map<const R43> points(input+56),force(input+68),target(input+80),refs(input+92),rest(input+104);
    Eigen::Map<const R42> allowed(input+116);double dt=input[172],speed=input[173],minimum=input[174],unit=speed*dt;
    if(!affine(body) || !affine(reference) || !(dt>0. && dt<=.2 && speed>0. && speed<=p.speed) || minimum!=p.min_force
      || force.col(2).minCoeff() < -1e-6) {throw std::invalid_argument("invalid XYZ input contract");}
    V lo=V::Constant(12,-1.),hi=V::Ones(12);lo.segment<2>(3*selected).setZero();hi.segment<2>(3*selected).setZero();
    for(int i=0;i<12;++i) {if(q(i)<p.physical(2*i) || q(i)>p.physical(2*i+1)
      || command(i)<p.physical(2*i) || command(i)>p.physical(2*i+1)) {throw std::invalid_argument("XYZ physical joint bound");}}
    for(int i=0;i<4;++i) {
      if((refs.row(i)-rest.row(i)).norm()>p.cap+1e-10 || allowed(i,0)>allowed(i,1)) {throw std::invalid_argument("XYZ original reference bounds");}
      lo(3*i+2)=std::max(-1.,(allowed(i,0)-refs(i,2))/unit);hi(3*i+2)=std::min(1.,(allowed(i,1)-refs(i,2))/unit);
      if(i==selected) {if((refs.row(i).head<2>()-rest.row(i).head<2>()).cwiseAbs().maxCoeff()>1e-12) {throw std::invalid_argument("XYZ selected XY");}lo(3*i+2)=std::max(0.,lo(3*i+2));}
    }
    if((lo-hi).maxCoeff()>1e-12) {throw std::invalid_argument("XYZ proven envelope");}hi=hi.cwiseMax(lo);
    M stiffness=M::Zero(12,12),b=M::Zero(12,6);std::array<M3,4> js;
    for(int i=0;i<4;++i) {
      js[i]=Eigen::Map<const R3>(input+124+9*i);M3 compliance=js[i]*p.gains.segment<3>(3*i).cwiseInverse().asDiagonal()*js[i].transpose();
      Eigen::SelfAdjointEigenSolver<M3> eigen(compliance);
      if(eigen.info()!=Eigen::Success || eigen.eigenvalues()(0)<1e-14) {throw std::invalid_argument("singular spatial contact compliance");}
      stiffness.block<3,3>(3*i,3*i)=compliance.inverse();b.block<3,3>(3*i,0).setIdentity();
      b.block<3,3>(3*i,3)=-skew(points.row(i).transpose()-body.block<3,1>(0,3));
    }
    M product=stiffness*b,system=b.transpose()*product;Eigen::JacobiSVD<M> sys_svd(system);
    if(!system.allFinite() || sys_svd.singularValues()(5)<=0. || sys_svd.singularValues()(0)/sys_svd.singularValues()(5)>1e12) {throw std::invalid_argument("singular floating body response");}
    M projector=stiffness-product*system.partialPivLu().solve(product.transpose());
    M response=-.5*(projector+projector.transpose()),a=response*unit;mark(0);
    Eigen::Map<const V> flat(force.data(),12),destination(target.data(),12);
    // Decision is a displacement, so a*x and the terminal error both use N.
    // dt still bounds every foot displacement; no force/rate bound is relaxed.
    // Keep the old 1/s error decay solely for independent legacy parity tests.
    V desired=(destination-flat)*(p.terminal_force ? 1. : dt),tau(12),servo=p.gains.array()*(command-q).array();
    M rows=M::Zero(132,12);V rhs(132);int row=0;V3 tangent=body.block<3,1>(0,0);tangent.z()=0.;
    if(tangent.norm()<1e-9) {throw std::invalid_argument("undefined flat tangent");}tangent.normalize();V3 second=V3::UnitZ().cross(tangent);
    for(int i=0;i<4;++i) {
      rows.row(row)=-a.row(3*i+2);rhs(row++)=force(i,2)-(i==selected ? 0. : minimum);
      for(const V3 & axis:std::array<V3,4>{tangent,-tangent,second,-second}) {V3 cone=axis;cone.z()-=1./std::sqrt(2.);
        rows.row(row)=cone.transpose()*a.middleRows<3>(3*i);rhs(row++)=-cone.dot(force.row(i));}
      tau.segment<3>(3*i)=gravity.segment<3>(3*i)-js[i].transpose()*force.row(i).transpose();
      M mapping=-js[i].transpose()*a.middleRows<3>(3*i);
      const auto servo_bound=servo_linearization(p.legs[i],command.segment<3>(3*i),reference,
        refs.row(i).transpose(),unit);
      for(int k=0;k<3;++k) {
        const double gain=p.gains(3*i+k);
        V position=V::Zero(12);position.segment<3>(3*i)=gain*servo_bound.displacement.row(k).transpose();
        for(double sign:{1.,-1.}) {
          rows.row(row)=sign*mapping.row(k);rhs(row++)=p.effort(3*i+k)-sign*tau(3*i+k);
          rows.row(row)=sign*position.transpose();rhs(row++)=p.effort(3*i+k)-gain*servo_bound.remainder-
            sign*(servo(3*i+k)+gain*servo_bound.bias(k));
        }
      }
    }
    for(int total=0;total<2;++total) {for(int i=0;i<4;++i) {for(int bits=0;bits<8;++bits) {
      V3 sign;for(int k=0;k<3;++k) {sign(k)=(bits&(1<<(2-k))) ? 1. : -1.;}
      rows.block<1,3>(row,3*i)=sign.transpose()*(total ? unit/p.cap : 1.);
      rhs(row++)=total ? 1.-sign.dot((refs.row(i)-rest.row(i)).transpose()/p.cap) : 1.;
    }}}
    if(row!=132) {throw std::runtime_error("XYZ row count");}
    Eigen::JacobiSVD<M> a_svd(a);double scale=std::max(a_svd.singularValues()(0)*a_svd.singularValues()(0),1e-12);
    M h=a.transpose()*a/scale+.001*M::Identity(12,12);V linear=-a.transpose()*desired/scale;
    bool origin=(-rhs).maxCoeff()<=1e-7 && lo.maxCoeff()<=1e-9 && hi.minCoeff()>=-1e-9;
    // Strict box implications preserve the complete feasible set, but prevent
    // the unconstrained start from spending pivots on box-redundant rows.
    // Every original132 row remains in the post-solve primal proof below.
    auto keep=integrated_robot_navigation_sensors::strict_box_rows(rows,rhs,lo,hi);
    // Unit L1 facets imply the omitted +/-1 coordinate bounds. Retain all of
    // them so box-implied row pruning has no circular logical dependency.
    constexpr Eigen::Index first_step_l1=68,step_l1_count=32;
    const auto solver_bounds=integrated_robot_navigation_sensors::l1_implied_unit_bounds(
      rows,rhs,first_step_l1,lo,hi);
    for(Eigen::Index r=first_step_l1;r<first_step_l1+step_l1_count;++r) {
      if(std::find(keep.begin(),keep.end(),r)==keep.end()) {keep.push_back(r);}
    }
    std::sort(keep.begin(),keep.end());
    M reduced(keep.size(),12);V reduced_rhs(keep.size());
    for(size_t i=0;i<keep.size();++i) {reduced.row(i)=rows.row(keep[i]);reduced_rhs(i)=rhs(keep[i]);}
    // Keep twelve physical displacement coordinates, but do not spend
    // active-set pivots on selected-foot XY equalities or their duplicate
    // one-coordinate L1 facets. Reconstruct before every original proof.
    auto problem=integrated_robot_navigation_sensors::eliminate_fixed_coordinates(
      h,linear,reduced,reduced_rhs,solver_bounds.first,solver_bounds.second);
    integrated_robot_navigation_sensors::equilibrate_all_constraints(problem);
    V alb=V::Constant(problem.b.size(),-std::numeric_limits<double>::infinity());
    V y=V::Zero(problem.g.size());mark(1);
    auto as_json=[](const M & value) {nlohmann::json out=nlohmann::json::array();
for(Eigen::Index r=0;r<value.rows();++r) {nlohmann::json row=nlohmann::json::array();
for(Eigen::Index c=0;c<value.cols();++c) {row.push_back(value(r,c));}out.push_back(row);}return out;};
nlohmann::json dump={{"a",as_json(rows)},{"b",as_json(rhs)},
{"lo",as_json(lo)},{"hi",as_json(hi)},{"h",as_json(h)},{"g",as_json(linear)}};
std::ofstream("/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2/Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/infeasible-264-e19a7f50-ac4a-480b-95db-1f0833782d85/problem.json")<<dump.dump();
auto status=p.solver.solve(y,problem.h,problem.g,problem.lo,problem.hi,
      problem.a,alb,problem.b,parameters());mark(2);
    if(status!=qpmad::Solver::OK) {throw std::runtime_error("native XYZ solver status "+std::to_string(int(status)));}
    const auto original=integrated_robot_navigation_sensors::canonicalize_original_primal(
      problem.reconstruct(y),rows,rhs,lo,hi);
    const V & x=original.value;const double residual=original.residual;
    V delta=x*unit,predicted=flat+response*delta,predicted_tau(12);
    for(int i=0;i<4;++i) {predicted_tau.segment<3>(3*i)=gravity.segment<3>(3*i)-js[i].transpose()*predicted.segment<3>(3*i);}
    std::array<double,208> result{};std::copy(delta.data(),delta.data()+12,result.begin());
    for(int i=0;i<12;++i) {for(int j=0;j<12;++j) {result[12+12*i+j]=response(i,j);}}
    std::copy(predicted.data(),predicted.data()+12,result.begin()+156);std::copy(predicted_tau.data(),predicted_tau.data()+12,result.begin()+168);
    std::copy(tau.data(),tau.data()+12,result.begin()+180);std::copy(servo.data(),servo.data()+12,result.begin()+192);
    result[204]=residual;result[205]=origin ? 1. : 0.;result[206]=double(p.solver.getNumberOfInequalityIterations());
    result[207]=(a*x-desired).squaredNorm()/scale+.001*x.squaredNorm();
    for(double v:result) {if(!std::isfinite(v)) {throw std::runtime_error("nonfinite XYZ result");}}mark(3);
    std::copy(result.begin(),result.end(),output);return 0;
  } catch(const std::exception & e) {if(error && error_size) {std::snprintf(error,error_size,"%s",e.what());}return 2;}
}

// Compose the existing three arithmetic ABIs without returning through Python.
// All plans remain owned by the numerical child. Output commits only after
// the same QP, all 28 geometry samples and nonlinear servo proof have passed.
extern "C" int ch13_mass_contact_terms(const void *,const double *,size_t,
  const double *,const double *,const size_t *,size_t,double *,double *) noexcept;
extern "C" int ch13_reference_evaluate(void *,const double *,size_t,int,double *,size_t);
extern "C" int ch13_xyz_complete_abi_version() {return 1;}
extern "C" int ch13_xyz_complete_evaluate(void * handle,const void * mass,void * geometry,
  const double * input,size_t count,size_t nq,const size_t * indices,size_t index_count,int selected,
  double budget_ns,double * output,size_t output_size,double * timings,size_t timing_size,
  char * error,size_t error_size) {
  if(!handle || !mass || !geometry || !input || !indices || !output || !timings
    || nq==0 || nq>64 || count!=nq+127 || index_count!=12 || selected<0 || selected>3
    || output_size!=220 || timing_size!=12 || !std::isfinite(budget_ns)
    || budget_ns<=0. || budget_ns>10000000.) {return 1;}
  std::fill(timings,timings+12,0.);
  try {
    const double start=ns(CLOCK_MONOTONIC),cpu=ns(CLOCK_THREAD_CPUTIME_ID);
    auto mark=[&](int i) {
      timings[2*i]=ns(CLOCK_MONOTONIC)-start;timings[2*i+1]=ns(CLOCK_THREAD_CPUTIME_ID)-cpu;
      if(timings[2*i]>budget_ns) {throw std::runtime_error("complete XYZ time budget");}
    };
    for(size_t i=0;i<count;++i) {if(!std::isfinite(input[i])) {throw std::invalid_argument("nonfinite complete XYZ input");}}
    for(size_t i=0;i<12;++i) {if(!indices[i] || indices[i]>nq) {throw std::invalid_argument("complete XYZ joint index");}}
    const double * a=input+nq;
    std::array<double,175> qp{};std::array<double,208> result{};std::array<double,8> stages{};
    for(size_t i=0;i<12;++i) {qp[i]=input[indices[i]-1];}
    std::copy(a,a+112,qp.begin()+12); // command through allowed_z
    const int contact=ch13_mass_contact_terms(mass,input,nq,a+12,a+44,indices,12,qp.data()+124,qp.data()+160);
    if(contact) {throw std::invalid_argument("complete XYZ contact rejected: "+std::to_string(contact));}
    std::copy(a+124,a+127,qp.begin()+172);mark(0);
    const double offset=ns(CLOCK_MONOTONIC)-start,offset_cpu=ns(CLOCK_THREAD_CPUTIME_ID)-cpu;
    const int code=ch13_xyz_evaluate(handle,qp.data(),qp.size(),selected,result.data(),result.size(),
      stages.data(),stages.size(),error,error_size);
    for(int i=0;i<4;++i) {if(stages[2*i]>0.) {
      timings[2*(i+1)]=offset+stages[2*i];timings[2*(i+1)+1]=offset_cpu+stages[2*i+1];
    }}
    if(code) {return code;}
    if(ns(CLOCK_MONOTONIC)-start>budget_ns) {throw std::runtime_error("complete XYZ time budget after QP");}
    if((result[205]!=0. && result[205]!=1.) || result[206]<0. || result[206]>32. || result[204]>1e-7) {
      throw std::runtime_error("complete XYZ native proof invalid");
    }
    Eigen::Map<const R4> reference(a+28);
    if(!affine(reference) || reference.row(3).head<3>().cwiseAbs().maxCoeff()>1e-12) {
      throw std::invalid_argument("complete XYZ affine reference required");
    }
    Eigen::FullPivLU<R4> inverse_plan(reference);
    // Test exact nonsingularity; do not replace the general affine inverse
    // with a rigid transpose or impose an extra conditioning threshold.
    inverse_plan.setThreshold(0.);
    if(!inverse_plan.isInvertible()) {throw std::invalid_argument("complete XYZ singular reference");}
    const R4 inverse=inverse_plan.inverse();
    std::array<double,60> geo{};std::array<double,40> checked{};std::array<double,220> complete{};
    std::copy(qp.begin(),qp.begin()+12,geo.begin());std::copy(inverse.data(),inverse.data()+16,geo.begin()+12);
    for(size_t i=0;i<12;++i) {geo[28+i]=a[80+i]+result[i];}
    std::copy(a+104,a+112,geo.begin()+40);std::copy(a+112,a+124,geo.begin()+48);
    const int geometry_code=ch13_reference_evaluate(geometry,geo.data(),geo.size(),selected,checked.data(),checked.size());
    if(geometry_code) {throw std::invalid_argument("complete XYZ future geometry rejected: "+std::to_string(geometry_code));}
    for(size_t i=0;i<checked.size();++i) {
      if(!std::isfinite(checked[i]) || (i>=12 && checked[i]<0.)) {throw std::invalid_argument("complete XYZ geometry proof");}
    }
    const auto & p=*static_cast<const Plan *>(handle);
    const R4 command_reference=Eigen::Map<const R4>(qp.data()+40);
    for(size_t leg=0;leg<4;++leg) {
      const V3 command=Eigen::Map<const V3>(qp.data()+12+3*leg);
      const V3 origin=Eigen::Map<const V3>(qp.data()+92+3*leg);
      const auto bound=servo_linearization(p.legs[leg],command,command_reference,origin,qp[172]*qp[173]);
      if((Eigen::Map<const V3>(checked.data()+3*leg)-command).norm()>bound.radius) {
        throw std::invalid_argument("complete XYZ inverse branch radius");
      }
    }
    std::copy(result.begin(),result.end(),complete.begin());
    for(size_t i=0;i<12;++i) {
      complete[208+i]=p.gains(i)*(checked[i]-qp[i]);
      if(!std::isfinite(complete[208+i]) || std::abs(complete[208+i])>p.effort(i)+1e-6) {
        throw std::invalid_argument("complete XYZ nonlinear servo residual");
      }
    }
    mark(5);std::copy(complete.begin(),complete.end(),output);return 0;
  } catch(const std::exception & e) {if(error && error_size) {std::snprintf(error,error_size,"%s",e.what());}return 2;}
}
