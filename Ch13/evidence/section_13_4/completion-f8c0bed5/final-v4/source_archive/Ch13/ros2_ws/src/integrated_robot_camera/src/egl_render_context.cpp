/**
 * Copyright (c) 2026, United States Government, as represented by the
 * Administrator of the National Aeronautics and Space Administration.
 *
 * All rights reserved.
 *
 * This software is licensed under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License. You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

#include "egl_render_context.hpp"
#include <EGL/eglext.h>
#include <mutex>

namespace integrated_robot_camera
{
namespace
{
EGLDisplay process_display()
{
  static std::mutex mutex;
  static EGLDisplay initialized = EGL_NO_DISPLAY;
  std::lock_guard<std::mutex> lock(mutex);
  if (initialized != EGL_NO_DISPLAY) {return initialized;}
  auto display = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, nullptr);
  if (display == EGL_NO_DISPLAY) {return EGL_NO_DISPLAY;}
  EGLint major{}, minor{};
  if (!eglInitialize(display, &major, &minor)) {return EGL_NO_DISPLAY;}
  initialized = display;
  // No global destructor/eglTerminate: other users can share this connection.
  return initialized;
}
}  // namespace

bool EglRenderContext::initialize()
{
  close();
  touched_ = true;
  display_ = process_display();
  if (display_ == EGL_NO_DISPLAY) {close(); return false;}
  const EGLint attributes[] = {
    EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8,
    EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_DEPTH_SIZE, 24,
    EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT, EGL_NONE};
  EGLConfig config{};
  EGLint count{};
  if (!eglChooseConfig(display_, attributes, &config, 1, &count) || count == 0 ||
    !eglBindAPI(EGL_OPENGL_API)) {close(); return false;}
  context_ = eglCreateContext(display_, config, EGL_NO_CONTEXT, nullptr);
  if (context_ == EGL_NO_CONTEXT) {close(); return false;}
  const EGLint pbuffer[] = {EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE};
  surface_ = eglCreatePbufferSurface(display_, config, pbuffer);
  if (surface_ == EGL_NO_SURFACE ||
    !eglMakeCurrent(display_, surface_, surface_, context_)) {close(); return false;}
  return true;
}

bool EglRenderContext::current() const noexcept
{
  return context_ != EGL_NO_CONTEXT && eglGetCurrentContext() == context_;
}

void EglRenderContext::close() noexcept
{
  if (!touched_) {return;}
  if (current()) {eglMakeCurrent(display_, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);}
  if (surface_ != EGL_NO_SURFACE) {eglDestroySurface(display_, surface_);}
  if (context_ != EGL_NO_CONTEXT) {eglDestroyContext(display_, context_);}
  surface_ = EGL_NO_SURFACE;
  context_ = EGL_NO_CONTEXT;
  display_ = EGL_NO_DISPLAY;
  eglReleaseThread();
  touched_ = false;
}
}  // namespace integrated_robot_camera
