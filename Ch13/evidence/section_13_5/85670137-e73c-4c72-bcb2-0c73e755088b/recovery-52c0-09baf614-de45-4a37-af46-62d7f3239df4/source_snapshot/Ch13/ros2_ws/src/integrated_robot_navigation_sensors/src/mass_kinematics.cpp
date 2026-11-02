// SPDX-License-Identifier: Apache-2.0
// Pure arithmetic for Ch13's compiled mass plan. No ROS/simulator/commands,
// worker, measured-pose cache, time source or application permission.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <vector>
#include <nlohmann/json.hpp>

namespace
{
using Matrix=std::array<double,16>;
constexpr Matrix identity{1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
Matrix multiply(const Matrix & a,const Matrix & b)
{
  Matrix result{};
  for(size_t i=0;i<4;++i) {
    for(size_t j=0;j<4;++j) {
      for(size_t k=0;k<4;++k) {result[4*i+j]+=a[4*i+k]*b[4*k+j];}
    }
  }
  return result;
}
Matrix inverse_rigid(const Matrix & a)
{
  Matrix out=identity;
  for(size_t i=0;i<3;++i) {
    for(size_t j=0;j<3;++j) {out[4*i+j]=a[4*j+i];}
    out[4*i+3]=-(out[4*i]*a[3]+out[4*i+1]*a[7]+out[4*i+2]*a[11]);
  }
  return out;
}
template<size_t N> std::array<double,N> finite_array(const nlohmann::json & value)
{
  if(!value.is_array() || value.size()!=N) {throw std::invalid_argument("mass plan dimensions");}
  std::array<double,N> result{};
  for(size_t i=0;i<N;++i) {
    result[i]=value.at(i).get<double>();
    if(!std::isfinite(result[i])) {throw std::invalid_argument("nonfinite mass geometry");}
  }
  return result;
}
bool rigid(const Matrix & pose)
{
  for(double v:pose) {if(!std::isfinite(v)) {return false;}}
  // Match support.center_of_mass's original allclose/math.isclose checks.
  for(size_t j=0;j<4;++j) {
    const double target=j==3 ? 1. : 0.;
    if(std::abs(pose[12+j]-target)>1e-10+1e-5*std::abs(target)) {return false;}
  }
  for(size_t i=0;i<3;++i) {
    for(size_t j=0;j<3;++j) {
      double value=0.;
      for(size_t k=0;k<3;++k) {value+=pose[4*k+i]*pose[4*k+j];}
      const double target=i==j ? 1. : 0.;
      if(std::abs(value-target)>1e-8+1e-5*std::abs(target)) {return false;}
    }
  }
  const double det=pose[0]*(pose[5]*pose[10]-pose[6]*pose[9])
    -pose[1]*(pose[4]*pose[10]-pose[6]*pose[8])+pose[2]*(pose[4]*pose[9]-pose[5]*pose[8]);
  return std::abs(det-1.)<=std::max(1e-8,1e-9*std::max(1.,std::abs(det)));
}
struct Step
{
  size_t parent;
  Matrix origin;
  bool prismatic,bounded;
  std::array<double,3> axis;
  std::array<double,9> skew,squared;
  double lower{0.},upper{0.};
};
struct Moment {size_t owner;std::array<double,4> value;};
struct Plan
{
  std::vector<Step> steps;
  std::vector<Moment> moments;
  size_t base_owner;
  Matrix base_fixed;
  double total;
};
}

extern "C"
{
int ch13_mass_abi_version() noexcept {return 1;}
void * ch13_mass_create(const char * text,char * error,size_t capacity) noexcept
{
  try {
    if(!text) {throw std::invalid_argument("null mass plan");}
    const auto value=nlohmann::json::parse(text);
    auto plan=std::make_unique<Plan>();
    const auto & steps=value.at("steps");
    if(!steps.is_array() || steps.size()>64) {throw std::invalid_argument("bounded mass plan required");}
    for(const auto & row:steps) {
      Step step;
      step.parent=row.at("parent").get<size_t>();
      if(step.parent>plan->steps.size()) {throw std::invalid_argument("topological mass plan required");}
      step.origin=finite_array<16>(row.at("origin"));
      if(!rigid(step.origin)) {throw std::invalid_argument("rigid mass origin required");}
      const auto kind=row.at("kind").get<std::string>();
      if(kind!="prismatic" && kind!="revolute" && kind!="continuous") {throw std::invalid_argument("mass joint kind");}
      step.prismatic=kind=="prismatic";
      step.axis=finite_array<3>(row.at("axis"));
      step.skew=finite_array<9>(row.at("skew"));step.squared=finite_array<9>(row.at("squared"));
      step.bounded=!row.at("bounds").is_null();
      if(step.bounded) {
        auto bounds=finite_array<2>(row.at("bounds"));step.lower=bounds[0];step.upper=bounds[1];
        if(step.lower>step.upper) {throw std::invalid_argument("mass joint bounds");}
      }
      plan->steps.push_back(step);
    }
    const auto & moments=value.at("moments");
    if(!moments.is_array() || moments.empty() || moments.size()>65) {throw std::invalid_argument("bounded mass moments required");}
    for(const auto & row:moments) {
      Moment moment{row.at("owner").get<size_t>(),finite_array<4>(row.at("value"))};
      if(moment.owner>steps.size() || moment.value[3]<=0.) {throw std::invalid_argument("mass moment owner/weight");}
      plan->moments.push_back(moment);
    }
    plan->base_owner=value.at("base_owner").get<size_t>();
    plan->base_fixed=finite_array<16>(value.at("base_fixed"));
    plan->total=value.at("total").get<double>();
    if(plan->base_owner>steps.size() || !rigid(plan->base_fixed)
      || !std::isfinite(plan->total) || plan->total<=0.) {throw std::invalid_argument("mass base/total");}
    return plan.release();
  } catch(const std::exception & problem) {
    if(error && capacity) {std::snprintf(error,capacity,"%s",problem.what());}
    return nullptr;
  } catch(...) {return nullptr;}
}
void ch13_mass_destroy(void * handle) noexcept {delete static_cast<Plan *>(handle);}
int ch13_mass_evaluate(const void * handle,const double * q,size_t count,
  const double * pose_data,double * result) noexcept
{
  if(!handle || !pose_data || !result) {return 1;}
  const auto & plan=*static_cast<const Plan *>(handle);
  if(count!=plan.steps.size() || count>64 || (count && !q)) {return 1;}
  Matrix pose;std::copy_n(pose_data,16,pose.begin());
  if(!rigid(pose)) {return 2;}
  std::array<Matrix,65> frames;frames[0]=identity;
  for(size_t n=0;n<count;++n) {
    const auto & step=plan.steps[n];const double value=q[n];
    if(!std::isfinite(value) || (step.bounded && (value<step.lower || value>step.upper))) {return 3;}
    Matrix change=identity;
    if(step.prismatic) {
      for(size_t i=0;i<3;++i) {change[4*i+3]=step.axis[i]*value;}
    } else {
      const double sine=std::sin(value),cosine=1.-std::cos(value);
      for(size_t i=0;i<3;++i) {
        for(size_t j=0;j<3;++j) {change[4*i+j]+=sine*step.skew[3*i+j]+cosine*step.squared[3*i+j];}
      }
    }
    frames[n+1]=multiply(multiply(frames[step.parent],step.origin),change);
  }
  std::array<double,4> moment{};
  for(const auto & part:plan.moments) {
    const auto & frame=frames[part.owner];
    for(size_t i=0;i<4;++i) {
      for(size_t j=0;j<4;++j) {moment[i]+=frame[4*i+j]*part.value[j];}
    }
  }
  const auto world=multiply(pose,inverse_rigid(multiply(frames[plan.base_owner],plan.base_fixed)));
  for(size_t i=0;i<3;++i) {
    result[i]=0.;
    for(size_t j=0;j<4;++j) {result[i]+=world[4*i+j]*moment[j];}
    result[i]/=plan.total;
    if(!std::isfinite(result[i])) {return 4;}
  }
  return 0;
}
}
