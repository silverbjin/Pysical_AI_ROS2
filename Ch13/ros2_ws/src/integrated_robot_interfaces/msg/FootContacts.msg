# Native measurements in header.frame_id (odom), positions in m and forces in N.
std_msgs/Header header
uint64 epoch
uint64 sequence
string[4] names
geometry_msgs/Point[4] points
float64[4] normal_forces
bool[4] touching
# Any active contact other than the four named feet against the ground.
uint32 unexpected_contacts
# Signed force ON each mapped foot, in the same world frame and capture.
# False means unavailable/unverified; normal_forces alone cannot attest it.
geometry_msgs/Vector3[4] forces_world
bool force_vectors_valid
