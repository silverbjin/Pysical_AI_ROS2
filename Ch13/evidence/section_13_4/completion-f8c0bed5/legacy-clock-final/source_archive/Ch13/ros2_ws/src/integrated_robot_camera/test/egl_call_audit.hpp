// SPDX-License-Identifier: Apache-2.0
// Test-executable interposition only. Successful EGL/GL calls reach the real driver.
#pragma once
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GL/gl.h>
#include <dlfcn.h>
#include <atomic>
#include <cstdlib>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace egl_audit
{
enum Failure {NONE, DISPLAY, INITIALIZE, CONFIG, BIND, CONTEXT, SURFACE, CURRENT};
inline std::atomic<int> failure{NONE}, glfw_calls{0}, terminate_calls{0};
inline std::atomic<int> contexts{0}, surfaces{0};
inline std::mutex mutex;
inline std::vector<std::pair<std::string, std::thread::id>> events;
inline void record(const char * name)
{
  std::lock_guard<std::mutex> lock(mutex);
  events.emplace_back(name, std::this_thread::get_id());
}
inline bool take(Failure point)
{
  int expected = point;
  return failure.compare_exchange_strong(expected, NONE);
}
template<class Function>
Function native(const char * name)
{
  auto function = reinterpret_cast<Function>(dlsym(RTLD_NEXT, name));
  if (!function) {std::abort();}
  return function;
}
inline void clear_events()
{
  std::lock_guard<std::mutex> lock(mutex);
  events.clear();
  glfw_calls = 0;
  terminate_calls = 0;
}
}  // namespace egl_audit

extern "C" int glfwInit()
{
  ++egl_audit::glfw_calls;
  // Force the old implementation through its real EGL fallback without invoking
  // the unsupported GLFW worker path in the test itself.
  return 0;
}
extern "C" EGLDisplay eglGetPlatformDisplay(EGLenum platform, void * display, const EGLAttrib * attrs)
{
  egl_audit::record("display");
  if (egl_audit::take(egl_audit::DISPLAY)) {return EGL_NO_DISPLAY;}
  return egl_audit::native<decltype(&eglGetPlatformDisplay)>("eglGetPlatformDisplay")(platform, display, attrs);
}
extern "C" EGLBoolean eglInitialize(EGLDisplay display, EGLint * major, EGLint * minor)
{
  egl_audit::record("initialize");
  if (egl_audit::take(egl_audit::INITIALIZE)) {return EGL_FALSE;}
  return egl_audit::native<decltype(&eglInitialize)>("eglInitialize")(display, major, minor);
}
extern "C" EGLBoolean eglChooseConfig(EGLDisplay display, const EGLint * attrs,
  EGLConfig * configs, EGLint size, EGLint * count)
{
  egl_audit::record("config");
  if (egl_audit::take(egl_audit::CONFIG)) {return EGL_FALSE;}
  return egl_audit::native<decltype(&eglChooseConfig)>("eglChooseConfig")(display, attrs, configs, size, count);
}
extern "C" EGLBoolean eglBindAPI(EGLenum api)
{
  egl_audit::record("bind");
  if (egl_audit::take(egl_audit::BIND)) {return EGL_FALSE;}
  return egl_audit::native<decltype(&eglBindAPI)>("eglBindAPI")(api);
}
extern "C" EGLContext eglCreateContext(EGLDisplay display, EGLConfig config,
  EGLContext shared, const EGLint * attrs)
{
  egl_audit::record("create_context");
  if (egl_audit::take(egl_audit::CONTEXT)) {return EGL_NO_CONTEXT;}
  auto context = egl_audit::native<decltype(&eglCreateContext)>("eglCreateContext")(display, config, shared, attrs);
  if (context != EGL_NO_CONTEXT) {++egl_audit::contexts;}
  return context;
}
extern "C" EGLSurface eglCreatePbufferSurface(EGLDisplay display, EGLConfig config, const EGLint * attrs)
{
  egl_audit::record("create_surface");
  if (egl_audit::take(egl_audit::SURFACE)) {return EGL_NO_SURFACE;}
  auto surface = egl_audit::native<decltype(&eglCreatePbufferSurface)>("eglCreatePbufferSurface")(display, config, attrs);
  if (surface != EGL_NO_SURFACE) {++egl_audit::surfaces;}
  return surface;
}
extern "C" EGLBoolean eglMakeCurrent(EGLDisplay display, EGLSurface draw, EGLSurface read, EGLContext context)
{
  egl_audit::record("current");
  if (context != EGL_NO_CONTEXT && egl_audit::take(egl_audit::CURRENT)) {return EGL_FALSE;}
  return egl_audit::native<decltype(&eglMakeCurrent)>("eglMakeCurrent")(display, draw, read, context);
}
extern "C" EGLBoolean eglDestroyContext(EGLDisplay display, EGLContext context)
{
  egl_audit::record("destroy_context");
  auto result = egl_audit::native<decltype(&eglDestroyContext)>("eglDestroyContext")(display, context);
  if (result) {--egl_audit::contexts;}
  return result;
}
extern "C" EGLBoolean eglDestroySurface(EGLDisplay display, EGLSurface surface)
{
  egl_audit::record("destroy_surface");
  auto result = egl_audit::native<decltype(&eglDestroySurface)>("eglDestroySurface")(display, surface);
  if (result) {--egl_audit::surfaces;}
  return result;
}
extern "C" EGLBoolean eglTerminate(EGLDisplay display)
{
  egl_audit::record("terminate");
  ++egl_audit::terminate_calls;
  return egl_audit::native<decltype(&eglTerminate)>("eglTerminate")(display);
}
extern "C" EGLBoolean eglReleaseThread()
{
  egl_audit::record("release_thread");
  return egl_audit::native<decltype(&eglReleaseThread)>("eglReleaseThread")();
}
