// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <Eigen/Core>
#include <Eigen/Cholesky>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace integrated_robot_navigation_sensors {
struct OriginalPrimal {
  Eigen::VectorXd value;
  double residual;
  size_t canonicalized;
};

// Retain the original1e-9 normalized box and1e-7 row proof. Only a box error
// ALREADY admitted by that proof may be represented as its exact boundary.
// Recheck ALL original rows afterwards: even tiny corrections cannot waive a
// coupled force/torque/L1 constraint. This precedes force/servo/geometry proofs,
// not application-time clipping of independently chosen foot commands.
inline OriginalPrimal canonicalize_original_primal(const Eigen::VectorXd & candidate,
  const Eigen::MatrixXd & a,const Eigen::VectorXd & b,
  const Eigen::VectorXd & lo,const Eigen::VectorXd & hi)
{
  if(candidate.size()<=0 || a.cols()!=candidate.size() || a.rows()!=b.size()
    || lo.size()!=candidate.size() || hi.size()!=candidate.size()
    || !candidate.allFinite() || !a.allFinite() || !b.allFinite()
    || !lo.allFinite() || !hi.allFinite() || (lo.array()>hi.array()).any()) {
    throw std::invalid_argument("invalid original QP primal proof");
  }
  if((lo-candidate).maxCoeff()>1e-9 || (candidate-hi).maxCoeff()>1e-9) {
    throw std::runtime_error("native XYZ primal residual");
  }
  OriginalPrimal out{candidate,0.,0};
  for(Eigen::Index i=0;i<candidate.size();++i) {
    if(out.value(i)<lo(i)) {out.value(i)=lo(i);++out.canonicalized;}
    else if(out.value(i)>hi(i)) {out.value(i)=hi(i);++out.canonicalized;}
  }
  out.residual=b.size() ? std::max(0.,(a*out.value-b).maxCoeff()) : 0.;
  if(out.residual>1e-7) {throw std::runtime_error("native XYZ primal residual");}
  return out;
}

// Exact substitution x=offset+E*y for coordinates whose ORIGINAL bounds are
// equal. No approximate equality, objective regularization, or row scaling.
// Singleton rows after substitution become bounds; zero rows must be feasible.
// Callers reconstruct and prove against the complete original problem.
struct FixedCoordinateQP {
  Eigen::MatrixXd h,a;
  Eigen::VectorXd g,b,lo,hi,offset;
  std::vector<Eigen::Index> free;
  Eigen::VectorXd reconstruct(const Eigen::VectorXd & y) const {
    if(y.size()!=static_cast<Eigen::Index>(free.size()) || !y.allFinite()) {
      throw std::invalid_argument("invalid reduced QP primal");
    }
    Eigen::VectorXd x=offset;
    for(size_t i=0;i<free.size();++i) {x(free[i])=y(i);}
    return x;
  }
};

inline FixedCoordinateQP eliminate_fixed_coordinates(
  const Eigen::MatrixXd & h,const Eigen::VectorXd & g,
  const Eigen::MatrixXd & a,const Eigen::VectorXd & b,
  const Eigen::VectorXd & lo,const Eigen::VectorXd & hi)
{
  const auto n=g.size();
  if(n<=0 || h.rows()!=n || h.cols()!=n || a.cols()!=n || a.rows()!=b.size()
    || lo.size()!=n || hi.size()!=n || !h.allFinite() || !g.allFinite()
    || !a.allFinite() || !b.allFinite() || lo.array().isNaN().any()
    || hi.array().isNaN().any() || (lo.array()>hi.array()).any()) {
    throw std::invalid_argument("invalid fixed coordinate QP");
  }
  FixedCoordinateQP out;out.offset=Eigen::VectorXd::Zero(n);
  for(Eigen::Index j=0;j<n;++j) {
    if(lo(j)==hi(j)) {
      if(!std::isfinite(lo(j))) {throw std::invalid_argument("nonfinite fixed QP bound");}
      out.offset(j)=lo(j);
    } else {out.free.push_back(j);}
  }
  const auto m=static_cast<Eigen::Index>(out.free.size());
  if(!m) {throw std::invalid_argument("no free QP coordinate");}
  out.h.resize(m,m);out.g.resize(m);out.lo.resize(m);out.hi.resize(m);
  const Eigen::VectorXd shifted_g=g+h*out.offset;
  for(Eigen::Index i=0;i<m;++i) {
    const auto original=out.free[i];out.g(i)=shifted_g(original);
    out.lo(i)=lo(original);out.hi(i)=hi(original);
    for(Eigen::Index j=0;j<m;++j) {out.h(i,j)=h(original,out.free[j]);}
  }
  out.a.resize(a.rows(),m);out.b=b-a*out.offset;
  for(Eigen::Index j=0;j<m;++j) {out.a.col(j)=a.col(out.free[j]);}
  Eigen::Index retained=0;
  for(Eigen::Index i=0;i<a.rows();++i) {
    Eigen::Index nonzero=0,column=-1;
    for(Eigen::Index j=0;j<m;++j) {if(out.a(i,j)!=0.) {++nonzero;column=j;}}
    if(!nonzero) {
      if(out.b(i)<0.) {throw std::invalid_argument("infeasible fixed QP row");}
    } else if(nonzero==1) {
      const auto coefficient=out.a(i,column);const double bound=out.b(i)/coefficient;
      if(!std::isfinite(bound)) {throw std::invalid_argument("nonfinite singleton QP bound");}
      if(coefficient>0.) {out.hi(column)=std::min(out.hi(column),bound);}
      else {out.lo(column)=std::max(out.lo(column),bound);}
    } else {
      if(retained!=i) {out.a.row(retained)=out.a.row(i);out.b(retained)=out.b(i);}
      ++retained;
    }
  }
  if((out.lo.array()>out.hi.array()).any()) {throw std::invalid_argument("infeasible singleton QP bounds");}
  out.a.conservativeResize(retained,m);out.b.conservativeResize(retained);
  return out;
}

// QPMAD prefers simple bounds before testing general constraints, then ranks
// raw violations. Give every inequality the same representation and measure
// its violation in the objective's metric: a/sqrt(a*H^-1*a^T). This positive
// scaling preserves the feasible set/objective, not an approximate penalty.
// The complete original primal checks remain mandatory after reconstruction.
inline void equilibrate_all_constraints(FixedCoordinateQP & problem)
{
  const auto n=problem.g.size();
  if(n<=0 || problem.h.rows()!=n || problem.h.cols()!=n || problem.a.cols()!=n
    || problem.a.rows()!=problem.b.size() || problem.lo.size()!=n || problem.hi.size()!=n
    || !problem.h.allFinite() || !problem.a.allFinite() || !problem.b.allFinite()
    || problem.lo.array().isNaN().any() || problem.hi.array().isNaN().any()
    || (problem.lo.array()>problem.hi.array()).any()) {
    throw std::invalid_argument("invalid metric QP");
  }
  Eigen::LLT<Eigen::MatrixXd> llt(problem.h);
  if(llt.info()!=Eigen::Success) {throw std::invalid_argument("nonpositive metric QP");}
  Eigen::Index count=problem.b.size();
  for(Eigen::Index i=0;i<n;++i) {count+=std::isfinite(problem.lo(i))+std::isfinite(problem.hi(i));}
  Eigen::MatrixXd rows(count,n);Eigen::VectorXd rhs(count);
  const auto original_rows=problem.b.size();rows.topRows(original_rows)=problem.a;
  rhs.head(original_rows)=problem.b;Eigen::Index next=original_rows;
  for(Eigen::Index i=0;i<n;++i) {
    if(std::isfinite(problem.lo(i))) {rows.row(next).setZero();rows(next,i)=-1.;rhs(next++)=-problem.lo(i);}
    if(std::isfinite(problem.hi(i))) {rows.row(next).setZero();rows(next,i)=1.;rhs(next++)=problem.hi(i);}
  }
  for(Eigen::Index i=0;i<count;++i) {
    const double length=std::sqrt(rows.row(i).dot(llt.solve(rows.row(i).transpose())));
    if(!std::isfinite(length) || length<=0.) {throw std::invalid_argument("invalid metric QP row");}
    rows.row(i)/=length;rhs(i)/=length;
  }
  if(!rows.allFinite() || !rhs.allFinite()) {throw std::invalid_argument("nonfinite equilibrated QP");}
  problem.a=std::move(rows);problem.b=std::move(rhs);
  problem.lo.resize(0);problem.hi.resize(0);
}
}  // namespace integrated_robot_navigation_sensors
