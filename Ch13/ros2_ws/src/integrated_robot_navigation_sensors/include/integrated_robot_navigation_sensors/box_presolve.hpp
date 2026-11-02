// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <Eigen/Core>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>
#include <utility>

namespace integrated_robot_navigation_sensors {
// A row can be omitted from the numerical solver only when the UNCHANGED
// variable box strictly implies it. Keep every uncertain/boundary row. Callers
// must still validate the reconstructed primal against ALL original rows.
inline std::vector<Eigen::Index> strict_box_rows(const Eigen::MatrixXd & a,
  const Eigen::VectorXd & b,const Eigen::VectorXd & lo,const Eigen::VectorXd & hi)
{
  if(a.rows()!=b.size() || a.cols()!=lo.size() || lo.size()!=hi.size()
    || !a.allFinite() || !b.allFinite() || !lo.allFinite() || !hi.allFinite()
    || (lo.array()>hi.array()).any()) {throw std::invalid_argument("invalid strict box presolve");}
  std::vector<Eigen::Index> keep;keep.reserve(a.rows());
  for(Eigen::Index r=0;r<a.rows();++r) {
    long double upper=0.,magnitude=1.+std::abs(static_cast<long double>(b(r)));
    for(Eigen::Index c=0;c<a.cols();++c) {
      const long double term=static_cast<long double>(a(r,c))*(a(r,c)>=0. ? hi(c) : lo(c));
      upper+=term;magnitude+=std::abs(term);
    }
    const long double guard=64.*std::numeric_limits<double>::epsilon()*magnitude;
    if(!(upper+guard<static_cast<long double>(b(r)))) {keep.push_back(r);}
  }
  return keep;
}

// Keep ALL eight canonical L1 facets per foot in the solver. They imply
// -1<=x_i<=1, so passing those same coordinate bounds as simple bounds wastes
// active-set pivots at cube corners. Non-unit/fixed/envelope bounds stay.
// Verify the actual matrix proof before relaxing any solver-only bound.
inline std::pair<Eigen::VectorXd,Eigen::VectorXd> l1_implied_unit_bounds(
  const Eigen::MatrixXd & a,const Eigen::VectorXd & b,Eigen::Index first,
  const Eigen::VectorXd & lo,const Eigen::VectorXd & hi)
{
  const auto n=lo.size();
  if(n<=0 || n%3 || a.cols()!=n || a.rows()!=b.size() || hi.size()!=n
    || first<0 || first+8*n/3>a.rows() || !lo.allFinite() || !hi.allFinite()
    || (lo.array()>hi.array()).any()) {throw std::invalid_argument("invalid L1 box implication");}
  for(Eigen::Index foot=0;foot<n/3;++foot) {for(int bits=0;bits<8;++bits) {
    const auto row=first+8*foot+bits;
    if(b(row)!=1.) {throw std::invalid_argument("missing canonical L1 bound");}
    for(Eigen::Index c=0;c<n;++c) {
      const double expected=c/3==foot ? ((bits&(1<<(2-c%3))) ? 1. : -1.) : 0.;
      if(a(row,c)!=expected) {throw std::invalid_argument("missing canonical L1 facet");}
    }
  }}
  Eigen::VectorXd lower=lo,upper=hi;
  for(Eigen::Index c=0;c<n;++c) {
    if(lo(c)==-1.) {lower(c)=-std::numeric_limits<double>::infinity();}
    if(hi(c)==1.) {upper(c)=std::numeric_limits<double>::infinity();}
  }
  return {lower,upper};
}
}  // namespace integrated_robot_navigation_sensors
