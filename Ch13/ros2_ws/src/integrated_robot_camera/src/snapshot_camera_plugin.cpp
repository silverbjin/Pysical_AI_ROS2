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

#include "snapshot_camera_plugin.hpp"
#include "egl_render_context.hpp"
#include <sys/syscall.h>
#include <unistd.h>

namespace integrated_robot_camera
{

bool SnapshotCameraPlugin::init(rclcpp::Node::SharedPtr node, const mjModel* model, mjData* data)
{
  std::lock_guard<std::mutex> lifecycle(lifecycle_mutex_);
  close();
  if (!node || !model || !data) {
    return false;
  }
  node_ = node;
  mj_model_ = model;
  try {
    auto state = std::make_shared<SelectionState>();
    if (!register_cameras(state)) {
      close();
      return false;
    }
    state->mailbox = std::make_shared<SnapshotMailbox>(model, cameras_.size());
    state->selected.reserve(cameras_.size());
    state->selected_polls.reserve(cameras_.size());
    state->stopped = false;
    std::atomic_store(&state_, state);
    const bool enabled = std::any_of(state->policies.begin(), state->policies.end(),
      [](CameraPolicy policy) {return policy != CameraPolicy::DISABLED;});
    if (!enabled) {return true;}
    std::promise<bool> ready;
    auto initialized = ready.get_future();
    rendering_thread_ = std::thread(&SnapshotCameraPlugin::update_loop, this, state, std::move(ready));
    if (!initialized.get()) {
      close();
      return false;
    }
    RCLCPP_INFO(logger_, "integrated_robot_camera/SnapshotCameraPlugin initialized");
    return true;
  } catch (const std::exception & error) {
    RCLCPP_ERROR(logger_, "Snapshot camera initialization failed: %s", error.what());
    close();
    return false;
  }
}

void SnapshotCameraPlugin::update(const mjModel* model_arg, mjData* data)
{
  auto state = std::atomic_load(&state_);
  if (!state || !data) {return;}
  try {
    // Called by the single control-thread producer with a stable control_data
    // snapshot, NOT physics live data. Mailbox and selection locks never nest.
    const auto observed = state->mailbox->observe_time(data->time);
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      if (state->stopped) {return;}
      if (observed.epoch != state->epoch || observed.rollback) {
        state->last_stream_time.reset();
        state->epoch = observed.epoch;
      }
      const bool due = !state->last_stream_time ||
        data->time - *state->last_stream_time >= 1. / state->rate;
      state->selected.clear();
      state->selected_polls.clear();
      for (size_t i = 0; i < state->policies.size(); ++i) {
        if ((state->policies[i] == CameraPolicy::STREAMING && due) ||
          (state->policies[i] == CameraPolicy::POLLED && state->polls[i]))
        {
          state->selected.push_back(i);
          if (state->policies[i] == CameraPolicy::POLLED) {state->selected_polls.push_back(i);}
          state->polls[i] = false;
        }
      }
      if (due) {state->last_stream_time = data->time;}
    }
    if (!state->selected.empty()) {
      state->mailbox->submit(model_arg, data, state->selected, observed.epoch, state->selected_polls);
    }
  } catch (const std::exception & error) {
    RCLCPP_ERROR(logger_, "Snapshot camera rejected input: %s", error.what());
  }
}

void SnapshotCameraPlugin::cleanup()
{
  std::lock_guard<std::mutex> lifecycle(lifecycle_mutex_);
  close();
}

void SnapshotCameraPlugin::on_reset(mjData * /*data*/)
{
  auto state = std::atomic_load(&state_);
  if (!state) {return;}
  state->mailbox->reset_epoch();
  std::lock_guard<std::mutex> lock(state->mutex);
  state->last_stream_time.reset();
  std::fill(state->polls.begin(), state->polls.end(), false);
}

bool SnapshotCameraPlugin::register_cameras(const std::shared_ptr<SelectionState> & state)
{
  const std::string param_prefix = "mujoco_plugins." + node_->get_sub_namespace() + ".";
  const std::string camera_publish_rate_param = param_prefix + "camera_publish_rate";
  if (!node_->has_parameter(camera_publish_rate_param))
  {
    node_->declare_parameter(camera_publish_rate_param, 5.0);
  }

  camera_publish_rate_ = node_->get_parameter(camera_publish_rate_param).as_double();
  if (!std::isfinite(camera_publish_rate_) || camera_publish_rate_ <= 0.) {return false;}
  state->rate = camera_publish_rate_;
  RCLCPP_INFO(node_->get_logger(), "Publishing camera data at rate %f per second.", camera_publish_rate_);

  cameras_.resize(0);
  for (auto i = 0; i < mj_model_->ncam; ++i)
  {
    const char* cam_name = mj_model_->names + mj_model_->name_camadr[i];
    const int* cam_resolution = mj_model_->cam_resolution + 2 * i;
    const mjtNum cam_fovy = mj_model_->cam_fovy[i];

    // Construct CameraData wrapper and set defaults
    CameraData camera;
    camera.name = cam_name;
    camera.mjv_cam.type = mjCAMERA_FIXED;
    camera.mjv_cam.fixedcamid = i;
    camera.width = static_cast<uint32_t>(cam_resolution[0]);
    camera.height = static_cast<uint32_t>(cam_resolution[1]);
    camera.viewport = { 0, 0, cam_resolution[0], cam_resolution[1] };

    const std::string param_ns = param_prefix + cam_name + ".";

    const std::string policy_param = param_ns + "policy";
    if (!node_->has_parameter(policy_param))
    {
      node_->declare_parameter(policy_param, "streaming");
    }
    std::string policy_str = node_->get_parameter(policy_param).as_string();
    if (policy_str == "streaming")
    {
      camera.policy = CameraPolicy::STREAMING;
    }
    else if (policy_str == "polled")
    {
      camera.policy = CameraPolicy::POLLED;
    }
    else if (policy_str == "disabled")
    {
      camera.policy = CameraPolicy::DISABLED;
    }
    else
    {
      RCLCPP_ERROR(node_->get_logger(), "Invalid policy for camera '%s'", cam_name);
      return false;
    }

    const std::string frame_param = param_ns + "frame_name";
    if (!node_->has_parameter(frame_param))
    {
      node_->declare_parameter(frame_param, camera.name + "_frame");
    }
    camera.frame_name = node_->get_parameter(frame_param).as_string();

    if (!node_->has_parameter(param_ns + "info_topic"))
    {
      node_->declare_parameter(param_ns + "info_topic", camera.name + "/camera_info");
    }
    camera.info_topic = node_->get_parameter(param_ns + "info_topic").as_string();

    if (!node_->has_parameter(param_ns + "image_topic"))
    {
      node_->declare_parameter(param_ns + "image_topic", camera.name + "/color");
    }
    camera.image_topic = node_->get_parameter(param_ns + "image_topic").as_string();

    if (!node_->has_parameter(param_ns + "depth_topic"))
    {
      node_->declare_parameter(param_ns + "depth_topic", camera.name + "/depth");
    }
    camera.depth_topic = node_->get_parameter(param_ns + "depth_topic").as_string();

    if (!node_->has_parameter(param_ns + "trigger_service_name"))
    {
      node_->declare_parameter(param_ns + "trigger_service_name", camera.name + "/trigger");
    }
    camera.trigger_service_name = node_->get_parameter(param_ns + "trigger_service_name").as_string();

    RCLCPP_INFO(node_->get_logger(), "Adding camera: '%s'", cam_name);
    RCLCPP_INFO(node_->get_logger(), "    policy: '%s'", policy_str.c_str());
    RCLCPP_INFO(node_->get_logger(), "    frame_name: '%s'", camera.frame_name.c_str());
    state->policies.push_back(camera.policy);
    state->polls.push_back(false);
    if (camera.policy == CameraPolicy::DISABLED)
    {
      cameras_.push_back(std::move(camera));
      continue;
    }
    if (!camera.width || !camera.height || !std::isfinite(cam_fovy) ||
      cam_fovy <= 0. || cam_fovy >= 180.) {return false;}
    RCLCPP_INFO(node_->get_logger(), "    info_topic: '%s'", camera.info_topic.c_str());
    RCLCPP_INFO(node_->get_logger(), "    image_topic: '%s'", camera.image_topic.c_str());
    RCLCPP_INFO(node_->get_logger(), "    depth_topic: '%s'", camera.depth_topic.c_str());
    if (camera.policy == CameraPolicy::POLLED)
    {
      RCLCPP_INFO(node_->get_logger(), "    trigger_service_name: '%s'", camera.trigger_service_name.c_str());
    }

    // Configure publishers and services
    camera.camera_info_pub = node_->create_publisher<sensor_msgs::msg::CameraInfo>(camera.info_topic, 1);
    camera.image_pub = node_->create_publisher<sensor_msgs::msg::Image>(camera.image_topic, 1);
    camera.depth_image_pub = node_->create_publisher<sensor_msgs::msg::Image>(camera.depth_topic, 1);
    if (camera.policy == CameraPolicy::POLLED)
    {
      camera.trigger_service = node_->create_service<std_srvs::srv::Trigger>(
          camera.trigger_service_name, [weak = std::weak_ptr<SelectionState>(state), i](
            const std::shared_ptr<std_srvs::srv::Trigger::Request>,
            std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
            if (auto selected = weak.lock()) {
              std::lock_guard<std::mutex> lock(selected->mutex);
              response->success = !selected->stopped;
              if (response->success) {selected->polls.at(i) = true;}
            } else {response->success = false;}
          });
    }
    // Setup containers for color image data
    camera.image.header.frame_id = camera.frame_name;

    const auto image_size = camera.width * camera.height * 3;
    camera.image_buffer.resize(image_size);
    camera.image.data.resize(image_size);
    camera.image.width = camera.width;
    camera.image.height = camera.height;
    camera.image.step = camera.width * 3;
    camera.image.encoding = sensor_msgs::image_encodings::RGB8;

    // Depth image data
    camera.depth_image.header.frame_id = camera.frame_name;
    camera.depth_buffer.resize(camera.width * camera.height);
    camera.depth_image.data.resize(camera.width * camera.height * sizeof(float));
    camera.depth_image.width = camera.width;
    camera.depth_image.height = camera.height;
    camera.depth_image.step = camera.width * sizeof(float);
    camera.depth_image.encoding = sensor_msgs::image_encodings::TYPE_32FC1;

    // Camera info
    camera.camera_info.header.frame_id = camera.frame_name;
    camera.camera_info.width = camera.width;
    camera.camera_info.height = camera.height;
    camera.camera_info.distortion_model = "plumb_bob";
    camera.camera_info.k.fill(0.0);
    camera.camera_info.r.fill(0.0);
    camera.camera_info.p.fill(0.0);
    camera.camera_info.d.resize(5, 0.0);

    double focal_scaling = (1.0 / std::tan((cam_fovy * M_PI / 180.0) / 2.0)) * camera.height / 2.0;
    camera.camera_info.k[0] = camera.camera_info.p[0] = focal_scaling;
    camera.camera_info.k[2] = camera.camera_info.p[2] = static_cast<double>(camera.width) / 2.0;
    camera.camera_info.k[4] = camera.camera_info.p[5] = focal_scaling;
    camera.camera_info.k[5] = camera.camera_info.p[6] = static_cast<double>(camera.height) / 2.0;
    camera.camera_info.k[8] = camera.camera_info.p[10] = 1.0;

    // Add to list of cameras
    cameras_.push_back(camera);
  }

  return true;
}

void SnapshotCameraPlugin::close()
{
  auto state = std::atomic_exchange(&state_, std::shared_ptr<SelectionState>{});
  if (state) {
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      state->stopped = true;
    }
    state->mailbox->request_stop();
  }
  if (rendering_thread_.joinable())
  {
    rendering_thread_.join();
  }
  cameras_.clear();
  node_.reset();
  mj_model_ = nullptr;
}


void SnapshotCameraPlugin::update_loop(std::shared_ptr<SelectionState> state, std::promise<bool> ready)
{
  EglRenderContext gl;
  bool has_scene = false;
  bool has_context = false;
  bool announced = false;
  mjv_defaultOption(&mjv_opt_);
  mjv_defaultScene(&mjv_scn_);
  mjr_defaultContext(&mjr_con_);
  struct ScopeExit
  {
    std::function<void()> action;
    ~ScopeExit() {action();}
  } release{[&] {
      if (has_context) {mjr_freeContext(&mjr_con_);}
      if (has_scene) {mjv_freeScene(&mjv_scn_);}
      // gl is destroyed AFTER this guard, on the same worker.
    }};
  try {
    if (!gl.initialize()) {
      RCLCPP_ERROR(logger_, "Snapshot EGL initialization failed; no renderer fallback");
      state->mailbox->request_stop();
      ready.set_value(false);
      return;
    }
    RCLCPP_INFO(logger_, "Snapshot renderer EGL: %s; vendor=%s; version=%s; worker_tid=%ld",
      reinterpret_cast<const char *>(glGetString(GL_RENDERER)),
      reinterpret_cast<const char *>(glGetString(GL_VENDOR)),
      reinterpret_cast<const char *>(glGetString(GL_VERSION)), syscall(SYS_gettid));
    mjv_opt_.flags[mjtVisFlag::mjVIS_RANGEFINDER] = 0;
    for (int i = 0; i < mjNGROUP; ++i) {mjv_opt_.sitegroup[i] = 0;}
    mjv_makeScene(mj_model_, &mjv_scn_, 2000);
    has_scene = true;
    mjr_makeContext(mj_model_, &mjr_con_, mjFONTSCALE_150);
    has_context = true;
    int max_width = 1, max_height = 1;
    for (const auto & camera : cameras_) {
      if (camera.policy == CameraPolicy::DISABLED) {continue;}
      max_width = std::max(max_width, static_cast<int>(camera.width));
      max_height = std::max(max_height, static_cast<int>(camera.height));
    }
    mjr_resizeOffscreen(max_width, max_height, &mjr_con_);
    ready.set_value(true);
    announced = true;
    while (auto lease = state->mailbox->wait_take()) {
      update_cameras(state, *lease);
    }
  } catch (const std::exception & error) {
    RCLCPP_ERROR(logger_, "Snapshot render worker failed: %s", error.what());
    state->mailbox->request_stop();
    if (!announced) {ready.set_value(false);}
  }
}

void SnapshotCameraPlugin::update_cameras(const std::shared_ptr<SelectionState> & state,
  const SnapshotMailbox::RenderLease & lease)
{
  if (!state->mailbox->is_current(lease.epoch())) {return;}
  mjr_setBuffer(mjFB_OFFSCREEN, &mjr_con_);

  camera_near_distance_ = static_cast<float>(mj_model_->vis.map.znear * mj_model_->stat.extent);
  const float far = static_cast<float>(mj_model_->vis.map.zfar * mj_model_->stat.extent);
  camera_depth_scale_ = 1.0f - camera_near_distance_ / far;

  // Use the snapshotted data's timestamp in the ROS header, as that is when the data was actually pulled.
  const rclcpp::Duration duration = rclcpp::Duration::from_seconds(lease.stamp_seconds());
  rclcpp::Time stamp(duration.nanoseconds(), RCL_ROS_TIME);

  for (const auto idx : lease.camera_indices())
  {
    if (!state->mailbox->is_current(lease.epoch())) {return;}
    render_and_publish_camera(cameras_.at(idx), stamp, lease, state);
  }
}

void SnapshotCameraPlugin::render_and_publish_camera(CameraData & camera, const rclcpp::Time & stamp,
  const SnapshotMailbox::RenderLease & lease, const std::shared_ptr<SelectionState> & state)
{
  // Step 1: Render the scene and copy images to relevant camera data containers.
  // Render scene
  mjv_updateScene(mj_model_, const_cast<mjData *>(lease.data()), &mjv_opt_, NULL,
    &camera.mjv_cam, mjCAT_ALL, &mjv_scn_);
  mjr_render(camera.viewport, &mjv_scn_, &mjr_con_);

  // Copy image into relevant buffers
  mjr_readPixels(camera.image_buffer.data(), camera.depth_buffer.data(), camera.viewport, &mjr_con_);

  // Step 2: Adjust the images and copy depth data.
  // Fix non-linear depth buffer and flip it vertically (OpenGL's origin is the bottom left)
  // https://github.com/google-deepmind/mujoco/blob/3.4.0/python/mujoco/renderer.py#L190
  auto* depth_out = reinterpret_cast<float*>(camera.depth_image.data.data());
  for (uint32_t h = 0; h < camera.height; ++h)
  {
    const float* src_row = camera.depth_buffer.data() + static_cast<size_t>(h) * camera.width;
    float* dst_row = depth_out + static_cast<size_t>(camera.height - 1 - h) * camera.width;
    for (uint32_t w = 0; w < camera.width; ++w)
    {
      dst_row[w] = camera_near_distance_ / (1.0f - src_row[w] * camera_depth_scale_);
    }
  }

  // OpenGL's coordinate system's origin is in the bottom left, so we invert the images row-by-row
  const auto row_size = camera.width * 3;
  for (uint32_t h = 0; h < camera.height; ++h)
  {
    const auto src_idx = h * row_size;
    const auto dest_idx = (camera.height - 1 - h) * row_size;
    std::memcpy(&camera.image.data[dest_idx], &camera.image_buffer[src_idx], row_size);
  }

  // Step 3: Publish the images and camera info.
  camera.image.header.stamp = stamp;
  camera.depth_image.header.stamp = stamp;
  camera.camera_info.header.stamp = stamp;

  if (state->mailbox->is_current(lease.epoch())) {camera.image_pub->publish(camera.image);}
  if (state->mailbox->is_current(lease.epoch())) {camera.depth_image_pub->publish(camera.depth_image);}
  if (state->mailbox->is_current(lease.epoch())) {camera.camera_info_pub->publish(camera.camera_info);}
}

}  // namespace integrated_robot_camera

// Export the plugin
PLUGINLIB_EXPORT_CLASS(integrated_robot_camera::SnapshotCameraPlugin,
                       mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase)
