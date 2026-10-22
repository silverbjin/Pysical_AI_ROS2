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

#pragma once
#include <EGL/egl.h>

namespace integrated_robot_camera
{
// Only use on its owning render worker. The EGLDisplay connection is process-wide;
// this object owns just its context/surface and never terminates that connection.
class EglRenderContext
{
public:
  EglRenderContext() = default;
  ~EglRenderContext() {close();}
  EglRenderContext(const EglRenderContext &) = delete;
  EglRenderContext & operator=(const EglRenderContext &) = delete;
  EglRenderContext(EglRenderContext &&) = delete;
  EglRenderContext & operator=(EglRenderContext &&) = delete;
  bool initialize();
  void close() noexcept;
  bool current() const noexcept;

private:
  EGLDisplay display_{EGL_NO_DISPLAY};
  EGLContext context_{EGL_NO_CONTEXT};
  EGLSurface surface_{EGL_NO_SURFACE};
  bool touched_{false};
};
}  // namespace integrated_robot_camera
