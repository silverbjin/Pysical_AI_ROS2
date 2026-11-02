// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <Eigen/Core>
#include <Eigen/LU>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace integrated_robot_navigation_sensors {
// A global Frobenius upper bound on the3x3x3 FK Hessian of the existing
// hip/thigh/calf geometry: |sin|,|cos|<=1 for every joint configuration.
inline double leg_forward_hessian_bound(double offset,double upper,double lower) {
  if(!std::isfinite(offset) || !std::isfinite(upper) || !std::isfinite(lower)
    || upper<=0. || lower<=0.) {throw std::invalid_argument("invalid leg Hessian bound");}
  const double sum=upper+lower,side=std::abs(offset)+sum;
  return std::sqrt(2.*side*side+7.*sum*sum+13.*lower*lower)*
    (1.+64.*std::numeric_limits<double>::epsilon());
}

struct InverseRemainder {
  Eigen::Matrix3d inverse;
  double inverse_norm_bound,radius,joint_remainder;
};

// For ||D²f||<=B, ||J^-1||<=a and ||dp||<=d, a ball of radius r satisfying
// a*d+a*B*r²/2<=r and a*B*r<1 admits the local inverse by contraction.
// r=2*a*d/(1+sqrt(1-2*a²*B*d)); this is the stable small-root formula.
// Verify the exact IK belongs to this ball before using its certificate.
inline InverseRemainder inverse_remainder(const Eigen::Matrix3d & j,double b,double d) {
  if(!j.allFinite() || !std::isfinite(b) || b<=0. || !std::isfinite(d) || d<0.
    || std::abs(j.determinant())<1e-18) {throw std::invalid_argument("invalid inverse remainder input");}
  InverseRemainder out;out.inverse=j.partialPivLu().solve(Eigen::Matrix3d::Identity());
  if(!out.inverse.allFinite()) {throw std::invalid_argument("nonfinite inverse remainder");}
  const double eps=64.*std::numeric_limits<double>::epsilon();
  const double residual=(j*out.inverse-Eigen::Matrix3d::Identity()).norm()+
    eps*(1.+j.norm()*out.inverse.norm());
  if(!std::isfinite(residual) || residual>=1.) {throw std::invalid_argument("uncertified Jacobian inverse");}
  out.inverse_norm_bound=out.inverse.norm()/(1.-residual)*(1.+eps);
  const double a=out.inverse_norm_bound,h=2.*a*a*b*d;
  if(!std::isfinite(h) || h>=1.) {throw std::invalid_argument("inverse remainder trust region");}
  out.radius=2.*a*d/(1.+std::sqrt(1.-h));
  out.radius+=eps*(1.+out.radius);
  if(a*b*out.radius>=1. || a*d+.5*a*b*out.radius*out.radius>out.radius) {
    throw std::invalid_argument("inverse remainder contraction proof");
  }
  out.joint_remainder=.5*a*b*out.radius*out.radius+a*residual*d+eps*(1.+a*d);
  return out;
}
}  // namespace integrated_robot_navigation_sensors
