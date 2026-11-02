// SPDX-License-Identifier: Apache-2.0
// Ch13's own Rx/Ry/Ry IK and capsule/box distance, batched at CURRENT inputs.
// No ROS, clock, worker, measured cache, actuator interface or application right.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <limits>
#include <memory>
#include <stdexcept>
#include <nlohmann/json.hpp>

namespace {
using V=std::array<double,3>;
template<size_t N> std::array<double,N> finite_array(const nlohmann::json & j) {
  if(!j.is_array() || j.size()!=N) {throw std::invalid_argument("reference plan dimensions");}
  std::array<double,N> a{};
  for(size_t i=0;i<N;++i) {a[i]=j.at(i).get<double>();if(!std::isfinite(a[i])) {throw std::invalid_argument("nonfinite reference plan");}}
  return a;
}
V transform(const std::array<double,16> & a,const V & p) {
  V v{};for(size_t i=0;i<3;++i) {v[i]=a[4*i]*p[0]+a[4*i+1]*p[1]+a[4*i+2]*p[2]+a[4*i+3];}return v;
}
double box_distance(const V & a,const V & b,const V & half) {
  V d{};std::array<double,8> cuts{};size_t count=2;cuts[1]=1.;
  for(size_t i=0;i<3;++i) {
    d[i]=b[i]-a[i];
    if(d[i]!=0.) {for(double edge:{-half[i],half[i]}) {double t=(edge-a[i])/d[i];if(t>0. && t<1.) {cuts[count++]=t;}}}
  }
  // At most eight cuts. Explicit bounded insertion sort also avoids the
  // generic library's sixteen-element insertion threshold on this small array.
  for(size_t i=1;i<count;++i) {
    double value=cuts[i];size_t j=i;
    while(j>0 && value<cuts[j-1]) {cuts[j]=cuts[j-1];--j;}
    cuts[j]=value;
  }
  double best=std::numeric_limits<double>::infinity();
  for(size_t k=1;k<count;++k) {
    double lo=cuts[k-1],hi=cuts[k],middle=(lo+hi)/2.,norm=0.,product=0.;
    for(size_t i=0;i<3;++i) {double v=a[i]+d[i]*middle;if(std::abs(v)>half[i]) {norm+=d[i]*d[i];product+=(a[i]-std::copysign(half[i],v))*d[i];}}
    double t=norm ? std::min(hi,std::max(lo,-product/norm)) : lo;double distance=0.;
    for(size_t i=0;i<3;++i) {double gap=std::max(std::abs(a[i]+d[i]*t)-half[i],0.);distance+=gap*gap;}
    best=std::min(best,distance);
  }
  return std::sqrt(best);
}
struct Leg {
  V hip,half;double offset,upper,lower,radius;
  std::array<double,6> physical,allowed;std::array<double,16> inverse;
  explicit Leg(const nlohmann::json & j):hip(finite_array<3>(j.at("hip"))),half(finite_array<3>(j.at("half"))),
    offset(j.at("offset").get<double>()),upper(j.at("upper").get<double>()),lower(j.at("lower").get<double>()),radius(j.at("radius").get<double>()),
    physical(finite_array<6>(j.at("physical"))),allowed(finite_array<6>(j.at("allowed"))),inverse(finite_array<16>(j.at("inverse"))) {
    if(!std::isfinite(offset) || !std::isfinite(upper) || !std::isfinite(lower) || !std::isfinite(radius)
      || upper<=0. || lower<=0. || radius<=0.) {throw std::invalid_argument("invalid leg lengths");}
    for(size_t i=0;i<3;++i) {if(half[i]<=0. || physical[2*i]>physical[2*i+1] || allowed[2*i]>allowed[2*i+1]
      || allowed[2*i]<physical[2*i] || allowed[2*i+1]>physical[2*i+1]) {throw std::invalid_argument("invalid leg bounds");}}
  }
  V forward(const V & q) const {
    double x=-upper*std::sin(q[1])-lower*std::sin(q[1]+q[2]),z=-upper*std::cos(q[1])-lower*std::cos(q[1]+q[2]);
    return {hip[0]+x,hip[1]+offset*std::cos(q[0])-z*std::sin(q[0]),hip[2]+offset*std::sin(q[0])+z*std::cos(q[0])};
  }
  V ik(const V & target,const V & previous) const {
    double x=target[0]-hip[0],y=target[1]-hip[1],z=target[2]-hip[2],radial=y*y+z*z-offset*offset;
    if(radial<=0. || !std::isfinite(radial)) {throw std::invalid_argument("unreachable hip offset");}
    constexpr double tau=6.283185307179586476925286766559;V best{};double score=std::numeric_limits<double>::infinity();
    for(double local_z:{-std::sqrt(radial),std::sqrt(radial)}) {
      double roll=std::atan2(z,y)-std::atan2(local_z,offset);roll=std::atan2(std::sin(roll),std::cos(roll));
      double cosine=(x*x+local_z*local_z-upper*upper-lower*lower)/(2.*upper*lower);
      if(!std::isfinite(cosine) || cosine < -1.-1e-12 || cosine > 1.+1e-12) {continue;}
      double knee_abs=std::acos(std::min(1.,std::max(-1.,cosine)));
      for(double knee:{knee_abs,-knee_abs}) {
        double thigh=std::atan2(-x,-local_z)-std::atan2(lower*std::sin(knee),upper+lower*std::cos(knee));
        double first=std::ceil((physical[2]-thigh)/tau),last=std::floor((physical[3]-thigh)/tau);
        for(double turn=first;turn<=last;turn+=1.) {
          V q{roll,thigh+turn*tau,knee};bool valid=true;
          for(size_t i=0;i<3;++i) {valid=valid && physical[2*i]<=q[i] && q[i]<=physical[2*i+1];}
          if(!valid) {continue;}V actual=forward(q);double error=0.,distance=0.;
          for(size_t i=0;i<3;++i) {error+=(actual[i]-target[i])*(actual[i]-target[i]);distance+=(q[i]-previous[i])*(q[i]-previous[i]);}
          if(error<1e-16 && distance<score) {best=q;score=distance;}
        }
      }
    }
    if(!std::isfinite(score)) {throw std::invalid_argument("unreachable target or joint limit");}return best;
  }
  double clearance(const V & q) const {
    double c=std::cos(q[0]),s=std::sin(q[0]);V a{hip[0],hip[1]+offset*c,hip[2]+offset*s};
    V b{a[0]-upper*std::sin(q[1]),a[1]+upper*std::cos(q[1])*s,a[2]-upper*std::cos(q[1])*c};
    return box_distance(transform(inverse,a),transform(inverse,b),half)-radius;
  }
};
struct Plan {std::array<Leg,4> legs;explicit Plan(const nlohmann::json & j):
  legs{Leg(j.at(0)),Leg(j.at(1)),Leg(j.at(2)),Leg(j.at(3))} {if(j.size()!=4) {throw std::invalid_argument("four legs required");}}};
}
extern "C" int ch13_reference_abi_version() {return 1;}
extern "C" void * ch13_reference_create(const char * payload,char * error,size_t size) {
  try {if(!payload) {throw std::invalid_argument("missing reference plan");}return new Plan(nlohmann::json::parse(payload));}
  catch(const std::exception & e) {if(error && size) {std::snprintf(error,size,"%s",e.what());}return nullptr;}
}
extern "C" void ch13_reference_destroy(void * handle) {delete static_cast<Plan *>(handle);}
extern "C" int ch13_reference_evaluate(void * handle,const double * input,size_t count,int selected,double * output,size_t size) {
  if(!handle || !input || !output || count!=60 || size!=40 || selected<0 || selected>3) {return 1;}
  for(size_t i=0;i<count;++i) {if(!std::isfinite(input[i])) {return 2;}}
  try {
    const auto & plan=*static_cast<const Plan *>(handle);std::array<double,16> inverse{};
    std::copy(input+12,input+28,inverse.begin());std::array<double,40> result{};
    for(size_t f=0;f<4;++f) {
      const Leg & leg=plan.legs[f];V seed{},position{},future{};
      for(size_t i=0;i<3;++i) {seed[i]=input[3*f+i];position[i]=input[28+3*f+i];future[i]=input[48+3*f+i];
        if(seed[i]<leg.physical[2*i] || seed[i]>leg.physical[2*i+1]) {return 3;}}
      double lo=input[40+2*f],hi=input[41+2*f];if(lo>hi) {return 3;}
      std::array<V,16> angles{};size_t used=1;angles[0]=leg.ik(transform(inverse,position),seed);
      for(size_t i=0;i<3;++i) {result[3*f+i]=angles[0][i];}
      for(size_t index=0;index<(static_cast<int>(f)==selected ? 5u : 1u);++index) {
        double u=.25*static_cast<double>(index),x=position[0]*(1.-u)+future[0]*u,y=position[1]*(1.-u)+future[1]*u;
        for(double z:{lo,(lo+hi)/2.,hi}) {angles[used++]=leg.ik(transform(inverse,{x,y,z}),seed);}
      }
      double clear=std::numeric_limits<double>::infinity();std::array<double,6> bounds;bounds.fill(clear);
      for(size_t k=0;k<used;++k) {
        clear=std::min(clear,leg.clearance(angles[k])-.0001);
        for(size_t i=0;i<3;++i) {bounds[2*i]=std::min(bounds[2*i],angles[k][i]-leg.allowed[2*i]);bounds[2*i+1]=std::min(bounds[2*i+1],leg.allowed[2*i+1]-angles[k][i]);}
      }
      result[12+f]=clear;std::copy(bounds.begin(),bounds.end(),result.begin()+16+6*f);
    }
    for(double v:result) {if(!std::isfinite(v)) {return 4;}}
    std::copy(result.begin(),result.end(),output);return 0;
  } catch(const std::exception &) {return 4;}
}
