// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/box_presolve.hpp"
#include "integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp"
#include "integrated_robot_navigation_sensors/inverse_remainder.hpp"
#include <gtest/gtest.h>
using integrated_robot_navigation_sensors::strict_box_rows;
using Eigen::MatrixXd;using Eigen::VectorXd;
using integrated_robot_navigation_sensors::eliminate_fixed_coordinates;
using integrated_robot_navigation_sensors::equilibrate_all_constraints;
using integrated_robot_navigation_sensors::canonicalize_original_primal;
using integrated_robot_navigation_sensors::inverse_remainder;
using integrated_robot_navigation_sensors::leg_forward_hessian_bound;

TEST(InverseRemainder,AnalyticCurvedInverseStaysInsideRadiusAndRemainderForBothSigns) {
  const double b=2.,d=.001;const auto proof=inverse_remainder(Eigen::Matrix3d::Identity(),b,d);
  for(int i=-100;i<=100;++i) {
    const double step=d*i/100.;const double exact=2.*step/(1.+std::sqrt(1.+2.*b*step));
    EXPECT_LE(std::abs(exact),proof.radius);
    EXPECT_LE(std::abs(exact-step),proof.joint_remainder);
  }
}
TEST(InverseRemainder,SingularOrUncertifiableTrustRegionsFailClosed) {
  EXPECT_THROW(inverse_remainder(Eigen::Matrix3d::Zero(),1.,.001),std::invalid_argument);
  EXPECT_THROW(inverse_remainder(.001*Eigen::Matrix3d::Identity(),2.,.001),std::invalid_argument);
  EXPECT_THROW(inverse_remainder(Eigen::Matrix3d::Identity(),1.,-.001),std::invalid_argument);
}
TEST(InverseRemainder,AnalyticLegHessiansRespectTheGlobalTrigonometricBound) {
  const double u=.213,l=.213,o=.08,b=leg_forward_hessian_bound(o,u,l);
  EXPECT_DOUBLE_EQ(b,leg_forward_hessian_bound(-o,u,l));
  for(double h:{-2.,-1.,0.,1.,2.}) {for(double t:{-2.,-1.,0.,1.,2.}) {
    for(double k:{-2.7,-2.,-1.3,-.6,-.3}) {
      const double c=std::cos(h),s=std::sin(h),a=u*std::cos(t)+l*std::cos(t+k);
      const double p=u*std::sin(t)+l*std::sin(t+k),v=l*std::sin(t+k),w=l*std::cos(t+k);
      Eigen::Matrix3d x,y,z;x<<0.,0.,0.,0.,p,v,0.,v,v;
      y<<-o*c-a*s,-p*c,-v*c,-p*c,-a*s,-w*s,-v*c,-w*s,-w*s;
      z<<-o*s+a*c,-p*s,-v*s,-p*s,a*c,w*c,-v*s,w*c,w*c;
      EXPECT_LE(std::sqrt(x.squaredNorm()+y.squaredNorm()+z.squaredNorm()),b);
    }
  }}
}

TEST(OriginalPrimal,OnlyPreviouslyAdmittedBoxRoundoffBecomesAnExactBoundary) {
  VectorXd x(3),lo(3),hi(3);x<<-1e-16,1.+5e-10,.25;lo<<0.,0.,-1.;hi<<1.,1.,1.;
  MatrixXd a=MatrixXd::Identity(3,3);VectorXd b=VectorXd::Ones(3);
  const auto out=canonicalize_original_primal(x,a,b,lo,hi);
  EXPECT_DOUBLE_EQ(out.value(0),0.);EXPECT_DOUBLE_EQ(out.value(1),1.);
  EXPECT_DOUBLE_EQ(out.value(2),x(2));EXPECT_EQ(out.canonicalized,2u);
  EXPECT_EQ(out.residual,0.);
}
TEST(OriginalPrimal,SignificantBoxErrorsAndNonfiniteInputsNeverProduceAResult) {
  VectorXd x(2),lo=VectorXd::Zero(2),hi=VectorXd::Ones(2),b=VectorXd::Ones(2);
  MatrixXd a=MatrixXd::Identity(2,2);x<<-2e-9,.5;
  EXPECT_THROW(canonicalize_original_primal(x,a,b,lo,hi),std::runtime_error);
  x<<.5,std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(canonicalize_original_primal(x,a,b,lo,hi),std::invalid_argument);
}
TEST(OriginalPrimal,CanonicalizationMustStillSatisfyTheCompleteOriginalCoupledRows) {
  VectorXd x(2),lo(2),hi=VectorXd::Ones(2),b=VectorXd::Zero(1);x<<-5e-10,5e-7;lo<<0.,-1.;
  MatrixXd a(1,2);a<<1e4,1.;
  ASSERT_LE((a*x-b).maxCoeff(),0.);
  // Making x0 exactly zero would violate this original row. It must fail,
  // rather than returning a box-feasible but coupled-infeasible vector.
  EXPECT_THROW(canonicalize_original_primal(x,a,b,lo,hi),std::runtime_error);
}

TEST(MetricQP,AllFiniteBoundsBecomeMetricUnitRowsWithUnchangedObjectiveAndFeasibleSet) {
  MatrixXd h(2,2);h<<4.,0.,0.,1.;VectorXd g(2);g<<3.,-2.;
  MatrixXd a(1,2);a<<2.,1.;VectorXd b=VectorXd::Constant(1,.4),lo(2),hi(2);
  lo<<-2.,.1;hi<<3.,std::numeric_limits<double>::infinity();
  auto problem=eliminate_fixed_coordinates(h,g,a,b,lo,hi);
  equilibrate_all_constraints(problem);
  ASSERT_EQ(problem.a.rows(),4);EXPECT_EQ(problem.lo.size(),0);EXPECT_EQ(problem.hi.size(),0);
  EXPECT_TRUE(problem.h.isApprox(h,0.));EXPECT_TRUE(problem.g.isApprox(g,0.));
  for(int r=0;r<problem.a.rows();++r) {
    const double x=problem.a(r,0),y=problem.a(r,1);
    EXPECT_NEAR(x*x/4.+y*y,1.,1e-12);
  }
  for(int i=-40;i<=40;++i) {for(int j=-40;j<=40;++j) {
    VectorXd y(2);y<<i*.1,j*.1;const auto x=problem.reconstruct(y);
    const bool original=(a*x-b).maxCoeff()<=1e-12 && (lo-x).maxCoeff()<=1e-12 && (x-hi).maxCoeff()<=1e-12;
    EXPECT_EQ(original,(problem.a*y-problem.b).maxCoeff()<=1e-12);
  }}
}
TEST(MetricQP,NonpositiveHessianAndZeroOrNonfiniteRowsFailClosed) {
  MatrixXd h=MatrixXd::Identity(2,2),a=MatrixXd::Ones(1,2);
  VectorXd g=VectorXd::Zero(2),b=VectorXd::Ones(1),lo=VectorXd::Constant(2,-1.),hi=VectorXd::Ones(2);
  const auto valid=eliminate_fixed_coordinates(h,g,a,b,lo,hi);
  auto problem=valid;problem.h(0,0)=-1.;EXPECT_THROW(equilibrate_all_constraints(problem),std::invalid_argument);
  problem=valid;problem.a.setZero();EXPECT_THROW(equilibrate_all_constraints(problem),std::invalid_argument);
  problem=valid;problem.b(0)=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(equilibrate_all_constraints(problem),std::invalid_argument);
}

TEST(FixedCoordinateQP,NonzeroFixedOffsetsPreserveObjectiveAndAllSingletonConstraints) {
  MatrixXd h(3,3);h<<4.,1.,.5,1.,3.,-2.,.5,-2.,5.;
  VectorXd g(3);g<<1.,-2.,3.;MatrixXd a(2,3);a<<1.,2.,3.,0.,-1.,0.;
  VectorXd b(2);b<<3.,1.;VectorXd lo(3),hi(3);lo<<2.,-5.,-1.;hi<<2.,5.,-1.;
  const auto reduced=eliminate_fixed_coordinates(h,g,a,b,lo,hi);
  ASSERT_EQ(reduced.free,(std::vector<Eigen::Index>{1}));
  EXPECT_EQ(reduced.a.rows(),0);EXPECT_DOUBLE_EQ(reduced.lo(0),-1.);
  EXPECT_DOUBLE_EQ(reduced.hi(0),2.);EXPECT_DOUBLE_EQ(reduced.h(0,0),3.);
  EXPECT_DOUBLE_EQ(reduced.g(0),2.);
  for(int i=-20;i<=40;++i) {
    VectorXd y(1);y<<i*.1;const auto x=reduced.reconstruct(y);
    EXPECT_DOUBLE_EQ(x(0),2.);EXPECT_DOUBLE_EQ(x(2),-1.);
    EXPECT_NEAR(.5*x.dot(h*x)+g.dot(x),.5*y.dot(reduced.h*y)+reduced.g.dot(y)+8.5,1e-12);
    const bool original=(a*x-b).maxCoeff()<=1e-12 && (lo-x).maxCoeff()<=1e-12 && (x-hi).maxCoeff()<=1e-12;
    EXPECT_EQ(original,(y-reduced.hi).maxCoeff()<=1e-12 && (reduced.lo-y).maxCoeff()<=1e-12);
  }
}
TEST(FixedCoordinateQP,GeneralRowsAndInfiniteFreeBoundsRemainEquivalentOnExteriorGrid) {
  MatrixXd a(3,3);a<<3.,1.,1.,0.,0.,2.,1.,0.,0.;VectorXd b(3);b<<.2,1.,0.;
  VectorXd lo(3),hi(3);const auto inf=std::numeric_limits<double>::infinity();
  lo<<0.,-inf,-inf;hi<<0.,inf,inf;
  const auto reduced=eliminate_fixed_coordinates(MatrixXd::Identity(3,3),VectorXd::Zero(3),a,b,lo,hi);
  ASSERT_EQ(reduced.a.rows(),1);EXPECT_DOUBLE_EQ(reduced.hi(1),.5);
  for(int i=-20;i<=20;++i) {for(int j=-20;j<=20;++j) {
    VectorXd y(2);y<<i*.1,j*.1;const auto x=reduced.reconstruct(y);
    EXPECT_EQ((a*x-b).maxCoeff()<=1e-12,
      (reduced.a*y-reduced.b).maxCoeff()<=1e-12 && (y-reduced.hi).maxCoeff()<=1e-12);
  }}
}
TEST(FixedCoordinateQP,OnlyExactEqualitiesAreEliminatedAndInfeasibilityFailsClosed) {
  MatrixXd a(1,2);a<<1.,0.;VectorXd b=VectorXd::Zero(1),lo=VectorXd::Zero(2),hi=VectorXd::Ones(2);
  hi(0)=1e-16;
  EXPECT_EQ(eliminate_fixed_coordinates(MatrixXd::Identity(2,2),VectorXd::Zero(2),a,b,lo,hi).free.size(),2u);
  lo(0)=hi(0)=2.;
  EXPECT_THROW(eliminate_fixed_coordinates(MatrixXd::Identity(2,2),VectorXd::Zero(2),a,b,lo,hi),std::invalid_argument);
  b(0)=3.;lo(1)=1.;hi(1)=0.;
  EXPECT_THROW(eliminate_fixed_coordinates(MatrixXd::Identity(2,2),VectorXd::Zero(2),a,b,lo,hi),std::invalid_argument);
}

TEST(BoxPresolve,OriginalAndPresolvedFeasibleSetsAgreeOnTheSameBox) {
  MatrixXd a(4,2);a<<1.,1.,-2.,0.,.1,.1,0.,1.;
  VectorXd b(4);b<<.5,3.,1.,1.;
  VectorXd lo=VectorXd::Constant(2,-1.),hi=VectorXd::Ones(2);
  const auto keep=strict_box_rows(a,b,lo,hi);
  ASSERT_EQ(keep,(std::vector<Eigen::Index>{0,3}));
  for(int i=0;i<=40;++i) {for(int j=0;j<=40;++j) {
    VectorXd x(2);x<<-1.+i*.05,-1.+j*.05;
    bool reduced=true;for(auto r:keep) {reduced=reduced && a.row(r).dot(x)<=b(r)+1e-12;}
    EXPECT_EQ(reduced,(a*x-b).maxCoeff()<=1e-12);
  }}
}
TEST(BoxPresolve,FixedCoordinatesAndNonzeroOffsetsUseOriginalBounds) {
  MatrixXd a(2,2);a<<100.,1.,-100.,-1.;VectorXd b(2);b<<200.5,-198.;
  VectorXd lo(2),hi(2);lo<<2.,-1.;hi<<2.,1.;
  EXPECT_EQ(strict_box_rows(a,b,lo,hi),(std::vector<Eigen::Index>{0}));
}
TEST(BoxPresolve,BoundaryAndRoundingUncertaintyAreNeverPruned) {
  MatrixXd a=MatrixXd::Ones(1,2);VectorXd b=VectorXd::Constant(1,2.+1e-15);
  EXPECT_EQ(strict_box_rows(a,b,VectorXd::Constant(2,-1.),VectorXd::Ones(2)).size(),1u);
}
TEST(BoxPresolve,InvalidInputsFailClosed) {
  MatrixXd a=MatrixXd::Ones(1,2);VectorXd b=VectorXd::Ones(1),lo=VectorXd::Zero(2),hi=VectorXd::Ones(2);
  hi(0)=-1.;EXPECT_THROW(strict_box_rows(a,b,lo,hi),std::invalid_argument);
  hi.setOnes();a(0,0)=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(strict_box_rows(a,b,lo,hi),std::invalid_argument);
}

MatrixXd facets() {
  MatrixXd a(8,3);
  for(int r=0;r<8;++r) {for(int c=0;c<3;++c) {a(r,c)=(r&(1<<(2-c))) ? 1. : -1.;}}
  return a;
}
TEST(BoxPresolve,L1FacetsImplyOmittedUnitBoundsOverOriginalAndExteriorGrid) {
  const auto a=facets();VectorXd b=VectorXd::Ones(8),lo=VectorXd::Constant(3,-1.),hi=VectorXd::Ones(3);
  const auto bounds=integrated_robot_navigation_sensors::l1_implied_unit_bounds(a,b,0,lo,hi);
  EXPECT_TRUE((bounds.first.array()==-std::numeric_limits<double>::infinity()).all());
  EXPECT_TRUE((bounds.second.array()==std::numeric_limits<double>::infinity()).all());
  for(int i=-8;i<=8;++i) {for(int j=-8;j<=8;++j) {for(int k=-8;k<=8;++k) {
    VectorXd x(3);x<<i*.25,j*.25,k*.25;
    const bool l1=(a*x-b).maxCoeff()<=1e-12;
    EXPECT_EQ(l1,l1 && (x-lo).minCoeff()>=-1e-12 && (hi-x).minCoeff()>=-1e-12);
  }}}
}
TEST(BoxPresolve,FixedAndNonunitEnvelopeBoundsStayAndMissingProofFailsClosed) {
  auto a=facets();VectorXd b=VectorXd::Ones(8),lo(3),hi(3);lo<<0.,-1.,-.2;hi<<0.,1.,.3;
  const auto bounds=integrated_robot_navigation_sensors::l1_implied_unit_bounds(a,b,0,lo,hi);
  EXPECT_EQ(bounds.first(0),0.);EXPECT_EQ(bounds.second(0),0.);
  EXPECT_EQ(bounds.first(2),-.2);EXPECT_EQ(bounds.second(2),.3);
  a(0,0)=-.9;
  EXPECT_THROW(integrated_robot_navigation_sensors::l1_implied_unit_bounds(a,b,0,lo,hi),std::invalid_argument);
}
