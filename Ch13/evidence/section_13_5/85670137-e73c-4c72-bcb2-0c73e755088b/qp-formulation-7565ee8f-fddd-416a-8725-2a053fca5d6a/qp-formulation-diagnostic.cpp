// SPDX-License-Identifier: Apache-2.0
// Offline causal comparison only: never installed or used by a controller.
#include <qpmad/solver.h>
#include <Eigen/Cholesky>
#include <nlohmann/json.hpp>
#include "integrated_robot_navigation_sensors/box_presolve.hpp"
#include "integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp"
#include <fstream>
#include <iostream>
#include <chrono>
using M=Eigen::MatrixXd;using V=Eigen::VectorXd;using J=nlohmann::json;
M matrix(const J & j) {M out(j.size(),j.at(0).size());for(int r=0;r<out.rows();++r) {
  for(int c=0;c<out.cols();++c) {out(r,c)=j.at(r).at(c).get<double>();}}return out;}
J vector(const V & x) {J out=J::array();for(int i=0;i<x.size();++i) {out.push_back(x(i));}return out;}
int main(int argc,char **argv) {
  if(argc!=2) {return 2;}std::ifstream stream(argv[1]);J in;stream>>in;
  const M h=matrix(in.at("h")),a=matrix(in.at("a_original"));
  const V g=matrix(in.at("g")),b=matrix(in.at("b_original")),lo=matrix(in.at("lower")),hi=matrix(in.at("upper"));
  auto keep=integrated_robot_navigation_sensors::strict_box_rows(a,b,lo,hi);
  const auto bounds=integrated_robot_navigation_sensors::l1_implied_unit_bounds(a,b,68,lo,hi);
  for(int r=68;r<100;++r) {if(std::find(keep.begin(),keep.end(),r)==keep.end()) {keep.push_back(r);}}
  std::sort(keep.begin(),keep.end());M reduced(keep.size(),12);V rhs(keep.size());
  for(size_t i=0;i<keep.size();++i) {reduced.row(i)=a.row(keep[i]);rhs(i)=b(keep[i]);}
  const auto problem=integrated_robot_navigation_sensors::eliminate_fixed_coordinates(h,g,reduced,rhs,bounds.first,bounds.second);
  const auto inf=std::numeric_limits<double>::infinity();J output=J::array();
  // These are three separately declared offline experiments, not a runtime
  // retry/fallback. Every one starts cold with the original32/tolerance1e-12.
  for(int mode=0;mode<3;++mode) {
    M ah=problem.h,rows=problem.a;V lower=problem.lo,upper=problem.hi,right=problem.b;
    if(mode) {
      int count=right.size();for(int i=0;i<lower.size();++i) {count+=std::isfinite(lower(i))+std::isfinite(upper(i));}
      const int old=right.size();rows.conservativeResize(count,ah.rows());right.conservativeResize(count);int r=old;
      for(int i=0;i<lower.size();++i) {
        if(std::isfinite(lower(i))) {rows.row(r).setZero();rows(r,i)=-1.;right(r++)=-lower(i);}
        if(std::isfinite(upper(i))) {rows.row(r).setZero();rows(r,i)=1.;right(r++)=upper(i);}
      }
      lower.resize(0);upper.resize(0);
      if(mode==2) {
        Eigen::LLT<M> llt(problem.h);
        if(llt.info()!=Eigen::Success) {return 3;}
        for(int r=0;r<rows.rows();++r) {
          const double norm=std::sqrt(rows.row(r).dot(llt.solve(rows.row(r).transpose())));
          if(!std::isfinite(norm) || norm<=0.) {return 4;}
          rows.row(r)/=norm;right(r)/=norm;
        }
      }
    }
    qpmad::Solver solver;solver.reserve(ah.rows(),lower.size(),rows.rows());
    qpmad::SolverParameters p;p.max_iter_=32;p.tolerance_=1e-12;p.hessian_type_=qpmad::SolverParameters::HESSIAN_LOWER_TRIANGULAR;
    V y=V::Zero(ah.rows()),alb=V::Constant(right.size(),-inf);
    const auto start=std::chrono::steady_clock::now();J result={{"mode",mode},{"free_coordinates",ah.rows()},{"general_rows",rows.rows()},{"simple_bounds",lower.size()}};
    try {
      const auto status=solver.solve(y,ah,problem.g,lower,upper,rows,alb,right,p);const V x=problem.reconstruct(y);
      result["status"]=int(status);result["iterations"]=solver.getNumberOfInequalityIterations();
      result["primal"]=vector(x);result["original_residual"]=(a*x-b).maxCoeff();
      result["original_box_residual"]=std::max((lo-x).maxCoeff(),(x-hi).maxCoeff());
      result["original_objective"]=.5*x.dot(h*x)+g.dot(x);
    } catch(const std::exception & error) {result["error"]=error.what();}
    result["solve_wall_ns"]=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
    output.push_back(result);
  }
  std::cout<<output.dump(2)<<'\n';
}
