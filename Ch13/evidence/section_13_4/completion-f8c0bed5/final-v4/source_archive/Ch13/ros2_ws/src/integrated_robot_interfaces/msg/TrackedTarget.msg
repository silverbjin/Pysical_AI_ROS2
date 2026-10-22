# Position describes the visible depth surface, not a grasp pose.
std_msgs/Header header
std_msgs/Header source_header
builtin_interfaces/Time processed_at
string track_id
string class_id
float32 score
geometry_msgs/Point position
float64[9] covariance
bool valid
# TRACKED, LOST, INVALID, TF_UNAVAILABLE, RESET
string status
