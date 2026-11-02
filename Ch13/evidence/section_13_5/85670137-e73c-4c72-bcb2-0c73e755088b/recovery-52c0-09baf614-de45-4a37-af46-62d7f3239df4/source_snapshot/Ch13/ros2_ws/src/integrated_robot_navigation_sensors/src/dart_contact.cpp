// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/dart_contact.hpp"
#include <dart/constraint/ContactConstraint.hpp>
#include <dlfcn.h>
#include <cmath>
#include <filesystem>
#include <mutex>
#include <stdexcept>

namespace integrated_robot_navigation_sensors
{
namespace {std::mutex mutex;bool claimed=false;}
DartContactState inspect_dart_contact()
{
  using Contact=dart::constraint::ContactConstraint;
  Dl_info provider{};
  if (!dladdr(reinterpret_cast<void *>(&Contact::getErrorAllowance),&provider) || !provider.dli_fname) {
    throw std::runtime_error("native DART contact getter provider unavailable");
  }
  const std::string version=CH13_DART_HEADER_VERSION;
  const auto library=std::filesystem::canonical(provider.dli_fname);
  if (version.empty() || library.filename().string().find("libdart.so."+version)==std::string::npos) {
    throw std::runtime_error("DART contact header/library version mismatch");
  }
  const double current=Contact::getErrorAllowance();
  if (!std::isfinite(current)) {throw std::runtime_error("nonfinite native DART contact allowance");}
  return {current,current,version,library.string()};
}
DartContactState configure_g1_dart_contact(double requested_m,size_t worlds,bool explicit_g1)
{
  std::lock_guard<std::mutex> lock(mutex);
  if (!explicit_g1 || worlds!=1 || !std::isfinite(requested_m) || requested_m!=.00005) {
    throw std::runtime_error("only explicit single-world G1 50um contact experiment is permitted");
  }
  if (claimed) {throw std::runtime_error("DART contact setting already has an owner");}
  auto report=inspect_dart_contact();
  if (report.before_m!=0.) {throw std::runtime_error("unexpected preexisting DART contact allowance");}
  dart::constraint::ContactConstraint::setErrorAllowance(requested_m);
  report.effective_m=inspect_dart_contact().effective_m;
  if (report.effective_m!=requested_m) {throw std::runtime_error("DART contact setting not applied");}
  claimed=true;  // process lifetime; no reset, retry or mutation during physics
  return report;
}
}
