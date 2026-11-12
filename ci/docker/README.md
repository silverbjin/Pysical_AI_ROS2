# Common Gazebo CI Docker image (Jazzy / Harmonic)

The image is built once per Actions run from `ci/docker/Dockerfile` and reused for three isolated chapter probes. The image is **not yet immutable** while its upstream base is tag-based; the first tested `main` push publishes to GHCR and records a registry digest in the Actions artifact. Later acceptance must also pin the base image digest and apt packages.

| Chapter | Actually executed in Docker | Not covered |
|---|---|---|
| Ch03 | `colcon build`, Xacro/check_urdf, book `my_world.sdf` headless Gazebo server, entity creation and live ROS `/clock` bridge | GUI screenshot and joint controller dynamics |
| Ch04 | build, static TF publish and `/tf_static` receipt | Gazebo physics and other TF lab scenarios |
| Ch05 | build, Xacro/check_urdf | controller activation, trajectories, physics and GUI |

Ch06/Ch07 and Ch09–Ch11 require distinct dependency/asset mapping and remain NOT_RUN. A single model parse is not a Gazebo integration PASS. Ch13 is excluded until third-party asset ownership and mission scope are independently verified.

Run manually from Actions > **Book Gazebo common Docker**, select `chapter=all` or an individual chapter. On PR it builds once and checks all three; on merge to `main` it also publishes `ghcr.io/silverbjin/pysical-ai-book-gazebo:jazzy-harmonic-20261112` **only if all checks pass**. When publishing is permitted, `published_registry_digest.txt` identifies the immutable image content. If GHCR publishing is blocked, retain local Docker checks as evidence and request package permission; do not invent a digest.

This uses the ROS 2 Jazzy/Gazebo Harmonic pairing provided by `ros-jazzy-ros-gz`, with official Docker `ros:jazzy-ros-base-noble` as the starting point. Host WSL2 GUI remains final manual acceptance.
