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

#include <algorithm>
#include <atomic>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#include "sensor_msgs/image_encodings.hpp"
#include "integrated_robot_camera/snapshot_mailbox.hpp"

#include <dlfcn.h>

#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GL/gl.h>
#include <mujoco/mujoco.h>

#include <rclcpp/node.hpp>
#include <rclcpp/publisher.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_srvs/srv/trigger.hpp>

#include <pluginlib/class_list_macros.hpp>

namespace integrated_robot_camera
{

/**
 * @brief Selects when a camera's images are rendered and published.
 */
enum class CameraPolicy
{
  DISABLED = 0,  // Publishing is disabled.
  STREAMING,     // Publishing is constant at the specified publish rate.
  POLLED         // Publishing happens only when triggered by a service.
};

/**
 * @brief Per-camera bookkeeping: configuration, buffers, and ROS publishers/service for one
 * MuJoCo camera.
 *
 * One instance exists per camera registered by SnapshotCameraPlugin::register_cameras(). Buffers and
 * messages are reused across renders to avoid reallocating on every publish.
 */
struct CameraData
{
  CameraPolicy policy = CameraPolicy::STREAMING;

  mjvCamera mjv_cam;
  mjrRect viewport;

  std::string name;
  std::string frame_name;
  std::string info_topic;
  std::string image_topic;
  std::string depth_topic;
  std::string trigger_service_name;

  uint32_t width;
  uint32_t height;

  std::vector<uint8_t> image_buffer;
  std::vector<float> depth_buffer;

  sensor_msgs::msg::Image image;
  sensor_msgs::msg::Image depth_image;
  sensor_msgs::msg::CameraInfo camera_info;

  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr image_pub;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr depth_image_pub;
  rclcpp::Publisher<sensor_msgs::msg::CameraInfo>::SharedPtr camera_info_pub;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr trigger_service;
};

/**
 * @brief Plugin that publishes the mujoco camera data to ROS 2 topics.
 *
 * Camera topics can be named in the ROS 2 controls plugins YAML config file
 * and loaded as node parameters.
 * If any of the parameters are not specified, default topic names will be assigned.
 * A user can provide topic names for multiple cameras as long as cameras are not named the same.
 * Name collision is resolved by last name in the yaml file.
 *
 * Plugin Parameters Structure (and default topics)
 * ---------------------------
 *
 * mujoco_camera_plugin:
 *   type: "integrated_robot_camera/SnapshotCameraPlugin"
 *   # All cameras will publish data at the same rate
 *   camera_publish_rate: 6.0
 *   <camera_name>:
 *     policy: <policy>  # "disabled", "polled", or "streaming"
 *     frame_name: <camera_name>_frame
 *     info_topic: <camera_name>/camera_info
 *     image_topic: <camera_name>/color
 *     depth_topic: <camera_name>/depth
 *     trigger_service_name: <camera_name>/trigger  # only used for polling camera policy
 *
 * Implementation notes
 * --------------------
 * If the camera name, in the parameters, does not match any of the mujoco cameras
 * the data will not be published to ROS topics.
 * If no camera parameters are given, but the mujoco_camera_plugin and its policy are
 * declared, the default policy (streaming), topics, and frame are used automatically.
 *
 */
class SnapshotCameraPlugin : public mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase
{
public:
  SnapshotCameraPlugin() = default;
  ~SnapshotCameraPlugin() override {cleanup();}

  bool init(rclcpp::Node::SharedPtr node, const mjModel* model, mjData* data) override;

  void update(const mjModel* model, mjData* data) override;
  void on_reset(mjData * data) override;
  void cleanup() override;

private:
  // ROS interfaces
  rclcpp::Logger logger_{ rclcpp::get_logger("SnapshotCameraPlugin") };

  /**
   * @brief Stops the camera processing thread and closes the relevant objects, call before shutdown.
   */
  void close();

  /**
   * @brief Parses camera information from the mujoco model and node parameters.
   * @return true if registering cameras succeeds, otherwise false.
   */
  struct SelectionState
  {
    std::mutex mutex;
    bool stopped{true};
    std::vector<CameraPolicy> policies;
    std::vector<bool> polls;
    std::vector<size_t> selected;  // single control-thread producer scratch, reserved at init
    std::vector<size_t> selected_polls;
    std::optional<double> last_stream_time;
    uint64_t epoch{0};
    double rate{15.};
    std::shared_ptr<SnapshotMailbox> mailbox;
  };
  bool register_cameras(const std::shared_ptr<SelectionState> & state);

  /**
   * @brief Initializes the rendering context and starts processing.
   */
  void update_loop(std::shared_ptr<SelectionState> state, std::promise<bool> ready);

  /**
   * @brief Renders and publishes every camera that is flagged to render.
   */
  void update_cameras(const std::shared_ptr<SelectionState> & state,
    const SnapshotMailbox::RenderLease & lease);

  /**
   * @brief Renders and publishes data for a specific camera.
   * @param camera The camera data structure.
   * @param stamp Timestamp applied to all messages published this step.
   */
  void render_and_publish_camera(CameraData & camera, const rclcpp::Time & stamp,
    const SnapshotMailbox::RenderLease & lease, const std::shared_ptr<SelectionState> & state);

  /**
   * @brief Handles a polled camera trigger to render and publish messages.
   * @param camera The camera data structure.
   */
  rclcpp::Node::SharedPtr node_;
  const mjModel * mj_model_{nullptr};
  // init/cleanup serialize resource lifetime, not the per-frame producer path.
  std::mutex lifecycle_mutex_;
  std::shared_ptr<SelectionState> state_;  // accessed with atomic_load/store/exchange

  // Image publishing rate (applies to streaming cameras only)
  double camera_publish_rate_{ 5.0 };

  // Rendering options for the cameras, currently hard coded to defaults
  mjvOption mjv_opt_;
  mjvScene mjv_scn_;
  mjrContext mjr_con_;

  // Scene parameters to keep around to avoid recomputing
  float camera_near_distance_;
  float camera_depth_scale_;

  // Containers for camera data and ROS constructs
  std::vector<CameraData> cameras_;

  // Camera processing thread and objects for syncing
  std::thread rendering_thread_;

};

}  // namespace integrated_robot_camera
