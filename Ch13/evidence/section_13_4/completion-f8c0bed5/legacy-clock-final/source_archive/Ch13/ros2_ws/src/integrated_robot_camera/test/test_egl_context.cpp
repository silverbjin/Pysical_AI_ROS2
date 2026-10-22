// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <chrono>
#include <cerrno>
#include <future>
#include <string>
#include <thread>
#include <vector>
#include "egl_render_context.hpp"
#include "egl_call_audit.hpp"

extern char ** environ;
using integrated_robot_camera::EglRenderContext;
using namespace std::chrono_literals;

namespace
{
// posix_spawn, not fork into a Mesa/ROS multithreaded process. Each cache-failure
// case starts a fresh executable, with a bounded wait on only that owned child.
int fresh_child(const std::string & filter)
{
  std::vector<std::string> strings;
  for (char ** entry = environ; *entry; ++entry) {
    std::string value(*entry);
    if (value.rfind("CH13_EGL_FAILURE_CHILD=", 0) != 0 &&
      value.rfind("GTEST_OUTPUT=", 0) != 0) {strings.push_back(std::move(value));}
  }
  strings.emplace_back("CH13_EGL_FAILURE_CHILD=1");
  std::vector<char *> environment;
  for (auto & value : strings) {environment.push_back(value.data());}
  environment.push_back(nullptr);
  std::string executable = "/proc/self/exe", selected = "--gtest_filter=" + filter;
  std::string no_output = "--gtest_output=";
  char * arguments[] = {executable.data(), selected.data(), no_output.data(), nullptr};
  pid_t pid{};
  if (posix_spawn(&pid, executable.c_str(), nullptr, nullptr, arguments, environment.data())) {return -1;}
  const auto deadline = std::chrono::steady_clock::now() + 20s;
  int status{};
  for (;;) {
    const auto waited = waitpid(pid, &status, WNOHANG);
    if (waited == pid) {break;}
    if (waited < 0) {
      if (errno == EINTR) {continue;}
      return -4;
    }
    if (std::chrono::steady_clock::now() > deadline) {
      kill(pid, SIGKILL);
      while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
      return -2;
    }
    std::this_thread::sleep_for(5ms);
  }
  return WIFEXITED(status) ? WEXITSTATUS(status) : -3;
}

class FailureTest : public ::testing::TestWithParam<int> {};

TEST_P(FailureTest, CleansUpAndReinitializes)
{
  if (!std::getenv("CH13_EGL_FAILURE_CHILD")) {
    const auto * info = ::testing::UnitTest::GetInstance()->current_test_info();
    EXPECT_EQ(fresh_child(std::string(info->test_suite_name()) + "." + info->name()), 0);
    return;
  }
  std::async(std::launch::async, [stage = GetParam()] {
    egl_audit::failure = stage;
    EglRenderContext context;
    EXPECT_FALSE(context.initialize()) << "injected EGL boundary " << stage;
    context.close();
    context.close();
    EXPECT_EQ(egl_audit::contexts.load(), 0);
    EXPECT_EQ(egl_audit::surfaces.load(), 0);
    EXPECT_EQ(egl_audit::terminate_calls.load(), 0);
    ASSERT_TRUE(context.initialize());  // explicit reinitialization, not an automatic retry
    EXPECT_TRUE(context.current());
    EXPECT_NE(glGetString(GL_RENDERER), nullptr);
    context.close();
    EXPECT_FALSE(context.current());
    EXPECT_EQ(egl_audit::contexts.load(), 0);
    EXPECT_EQ(egl_audit::surfaces.load(), 0);
    EXPECT_EQ(egl_audit::terminate_calls.load(), 0);
  }).get();
}
INSTANTIATE_TEST_SUITE_P(Boundaries, FailureTest, ::testing::Values(
  egl_audit::DISPLAY, egl_audit::INITIALIZE, egl_audit::CONFIG, egl_audit::BIND,
  egl_audit::CONTEXT, egl_audit::SURFACE, egl_audit::CURRENT));

TEST(EglContext, PrivateResourcesStayOnWorker)
{
  egl_audit::clear_events();
  const auto worker = std::async(std::launch::async, [] {
    const auto id = std::this_thread::get_id();
    EglRenderContext context;
    EXPECT_TRUE(context.initialize());
    EXPECT_TRUE(context.current());
    EXPECT_NE(glGetString(GL_RENDERER), nullptr);
    context.close();
    context.close();
    EXPECT_EQ(egl_audit::contexts.load(), 0);
    EXPECT_EQ(egl_audit::surfaces.load(), 0);
    return id;
  }).get();
  EXPECT_NE(worker, std::this_thread::get_id());
  ASSERT_FALSE(egl_audit::events.empty());
  for (const auto & event : egl_audit::events) {EXPECT_EQ(event.second, worker) << event.first;}
  EXPECT_EQ(egl_audit::terminate_calls.load(), 0);
}

TEST(EglContext, PeerContextSurvivesOtherContextCleanup)
{
  std::promise<bool> ready;
  auto initialized = ready.get_future();
  std::promise<void> finish;
  auto stopping = finish.get_future();
  auto peer = std::async(std::launch::async, [&] {
    EglRenderContext context;
    const bool ok = context.initialize();
    auto display = eglGetCurrentDisplay();
    auto current = eglGetCurrentContext();
    auto surface = eglGetCurrentSurface(EGL_DRAW);
    ready.set_value(ok);
    stopping.wait();
    if (ok) {
      EXPECT_TRUE(eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT));
      EXPECT_TRUE(eglMakeCurrent(display, surface, surface, current));
      EXPECT_NE(glGetString(GL_RENDERER), nullptr);
    }
  });
  const bool ok = initialized.get();
  if (ok) {
    std::async(std::launch::async, [] {
      EglRenderContext context;
      EXPECT_TRUE(context.initialize());
      context.close();
    }).get();
  }
  finish.set_value();
  peer.get();
  ASSERT_TRUE(ok);
  EXPECT_EQ(egl_audit::contexts.load(), 0);
  EXPECT_EQ(egl_audit::surfaces.load(), 0);
  EXPECT_EQ(egl_audit::terminate_calls.load(), 0);
}
}  // namespace
