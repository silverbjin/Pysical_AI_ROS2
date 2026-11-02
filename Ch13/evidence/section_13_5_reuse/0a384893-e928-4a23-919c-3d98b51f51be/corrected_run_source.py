def run(self):
    step_num = 1
    # Run the simulation
    while self.viewer.is_running():
        step_start = time.time()

        # Get the current state of the robot -----------------------------------------------------
        qpos, qvel = self.mjData.qpos, self.mjData.qvel
        base_lin_vel = mujoco_utils.base_lin_vel(self.mjData, frame='base')
        base_ang_vel = mujoco_utils.base_ang_vel(self.mjData, frame='base')
        base_ori_euler_xyz = mujoco_utils.base_ori_euler_xyz(self.mjData)
        heading_orientation_SO3 = mujoco_utils.heading_orientation_SO3(self.mjData)
        base_quat_wxyz = qpos[3:7]
        base_pos = mujoco_utils.base_pos(self.mjData)

        joints_pos_leg = qpos[7:19]
        joints_pos_arm = qpos[19:25]
        joints_pos_gripper = qpos[25]

        joints_vel_leg = qvel[6:18]
        joints_vel_arm = qvel[18:24]
        joints_vel_gripper = qvel[24]

        if(config.training_env["use_imu"] or config.training_env["use_concurrent_state_est"]):
            imu_linear_acceleration = self.mjData.sensordata[0:3]
            imu_angular_velocity = self.mjData.sensordata[3:6]
            imu_orientation = self.mjData.sensordata[9:13]
            #imu_orientation = base_quat_wxyz
        else:
            imu_linear_acceleration = np.zeros(3)
            imu_angular_velocity = np.zeros(3)
            imu_orientation = np.zeros(4)

        ref_base_lin_vel, ref_base_ang_vel = mujoco_utils.target_base_vel(self.mjData, self.ref_base_lin_vel_H, self.ref_base_ang_yaw_dot, frame='world')


        if(self.locomotion_policy.use_vision):
            self.heightmap.update_height_map(self.mjData.qpos[0:3], yaw=base_ori_euler_xyz[2])


        # IK controller --------------------------------------------------------------
        """reference_base_pose, \
            reference_joints_position, \
            ik_succeded = self.ik_mink_solver.compute(target_pos, target_quat, initial_joints_position, 
                                                    initial_base_pose, optimize_height=True, optimize_pitch=True)"""

        # RL controller --------------------------------------------------------------
        if self.console.isRLActivated and step_num % round(1 / (self.locomotion_policy.RL_FREQ * self.simulation_dt)) == 0:            

            """reference_base_pose, \
                reference_joints_position, \
                ik_succeded = self.ik_mink_solver.compute(target_pos, target_quat, initial_joints_position, 
                                                        initial_base_pose, optimize_height=True, optimize_pitch=True)"""

            self.desired_joint_pos_leg = self.locomotion_policy.compute_control(
                        base_pos=base_pos, 
                        base_ori_euler_xyz=base_ori_euler_xyz, 
                        base_quat_wxyz=base_quat_wxyz,
                        base_lin_vel=base_lin_vel, 
                        base_ang_vel=base_ang_vel,
                        heading_orientation_SO3=heading_orientation_SO3,
                        joints_pos_leg=joints_pos_leg, 
                        joints_vel_leg=joints_vel_leg,
                        joints_pos_arm=joints_pos_arm,
                        ref_base_lin_vel=ref_base_lin_vel, 
                        ref_base_ang_vel=ref_base_ang_vel,
                        ref_pose_command=self.desired_pose_command_overwrite,
                        imu_linear_acceleration=imu_linear_acceleration,
                        imu_angular_velocity=imu_angular_velocity,
                        imu_orientation=imu_orientation,
                        heightmap_data=self.heightmap.data if self.locomotion_policy.use_vision else None)

            self.Kp_legs = self.locomotion_policy.Kp_walking
            self.Kd_legs = self.locomotion_policy.Kd_walking

        else:
            # Go up-and-down
            self.Kp_legs = (self.locomotion_policy.Kp_walking if self.console.isRLActivated else self.locomotion_policy.Kp_stand_up_and_down)
            self.Kd_legs = (self.locomotion_policy.Kd_walking if self.console.isRLActivated else self.locomotion_policy.Kd_stand_up_and_down)

        # Torque saturation for the legs
        max_torque = self.mjModel.actuator_ctrlrange[0:12, 1]
        max_torque = max_torque*0.95  # A margin for safety
        lower = (-max_torque + self.Kd_legs * joints_vel_leg) / self.Kp_legs
        upper = ( max_torque + self.Kd_legs * joints_vel_leg) / self.Kp_legs

        self.desired_joint_pos_leg = np.clip(
            self.desired_joint_pos_leg,
            joints_pos_leg + lower,
            joints_pos_leg + upper
        )

        # PD controller --------------------------------------------------------------
        error_joints_pos_leg = self.desired_joint_pos_leg - joints_pos_leg
        tau_leg = self.Kp_legs*error_joints_pos_leg - self.Kd_legs*joints_vel_leg

        error_joints_pos_arm = self.desired_joint_pos_arm - joints_pos_arm
        tau_arm = self.Kp_arm*error_joints_pos_arm - self.Kd_arm*joints_vel_arm

        # Compute the inverse dynamics
        #M = np.zeros((self.mjModel.nv, self.mjModel.nv))
        #mujoco.mj_fullM(self.mjModel, M, self.mjData.qM)
        #M = M[18:24, 18:24]
        #tau_arm += M @ (self.Kp_arm * (error_joints_pos_arm) - self.Kd_arm * joints_vel_arm)
        #tau_arm += self.mjData.qfrc_bias[18:24]

        error_gripper_pos = self.desired_joint_pos_gripper - joints_pos_gripper
        tau_gripper = config.Kp_gripper*error_gripper_pos - config.Kd_gripper*joints_vel_gripper


        # Set control and mujoco step ----------------------------------------------------------------------
        self.mjData.ctrl[0:12] = tau_leg
        self.mjData.ctrl[12:18] = tau_arm 
        self.mjData.ctrl[18] = tau_gripper
        mujoco.mj_step(self.mjModel, self.mjData)
        step_num = step_num + 1


        # Sleep to match real-time ---------------------------------------------------------
        loop_elapsed_time = time.time() - step_start
        if(loop_elapsed_time < self.simulation_dt):
            time.sleep(self.simulation_dt - (loop_elapsed_time))


        # Render only at a certain frequency -----------------------------------------------------------------
        if time.time() - self.last_render_time > 1.0 / self.RENDER_FREQ:
            # Update the camera position
            self.viewer.cam.lookat[:] = base_pos
            self.viewer.sync()
            self.last_render_time = time.time()
