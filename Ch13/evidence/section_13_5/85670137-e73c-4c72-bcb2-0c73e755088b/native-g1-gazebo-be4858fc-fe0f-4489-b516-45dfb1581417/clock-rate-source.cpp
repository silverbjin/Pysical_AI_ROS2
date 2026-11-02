// Throwaway read-only clock characterization, not engine acceptance.
#include <rclcpp/rclcpp.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <nlohmann/json.hpp>
#include <chrono>
#include <fcntl.h>
#include <unistd.h>
#include <iomanip>
#include <set>
#include <sstream>
#include <vector>

int main(int argc, char ** argv)
{
  if (argc != 2) {return 2;}
  const std::string output = argv[1];
  rclcpp::init(argc,argv);
  auto node = std::make_shared<rclcpp::Node>("ch13_clock_rate_diagnostic");
  int64_t first = -1, last = -1;
  size_t count = 0, duplicates = 0, rollback = 0;
  std::vector<int64_t> deltas;
  std::set<std::string> owners;
  auto begin = std::chrono::steady_clock::now();
  auto subscription = node->create_subscription<rosgraph_msgs::msg::Clock>("/clock",
    rclcpp::QoS(rclcpp::KeepLast(1)).best_effort(),
    [&](const rosgraph_msgs::msg::Clock::ConstSharedPtr msg, const rclcpp::MessageInfo & info) {
      std::ostringstream gid;
      for (const auto value : info.get_rmw_message_info().publisher_gid.data) {
        gid << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(value);
      }
      owners.insert(gid.str());
      const int64_t stamp = rclcpp::Time(msg->clock).nanoseconds();
      if (first < 0) {first = stamp; begin = std::chrono::steady_clock::now();}
      else if (stamp == last) {++duplicates;}
      else if (stamp < last) {++rollback;}
      else {deltas.push_back(stamp-last);}
      last = stamp; ++count;
    });
  int result = 0;
  auto timer = node->create_wall_timer(std::chrono::seconds(5), [&] {
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    nlohmann::json report{{"scope","read_only_native_clock_rate_not_acceptance"},
      {"messages",count},{"first_stamp_ns",first},{"last_stamp_ns",last},
      {"wall_s",wall},{"duplicates",duplicates},{"rollback",rollback},
      {"publisher_gids",owners},{"positive_capture_deltas_ns",deltas}};
    if (!deltas.empty() && last > first) {
      report["capture_hz"] = deltas.size()*1e9/static_cast<double>(last-first);
      report["received_wall_hz"] = count/wall;
    } else {result = 3;}
    const auto raw = report.dump(2)+"\n";
    const int fd = ::open(output.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
    if (fd < 0 || ::write(fd,raw.data(),raw.size()) != static_cast<ssize_t>(raw.size())) {result = 4;}
    if (fd >= 0) {::close(fd);}
    rclcpp::shutdown();
  });
  rclcpp::spin(node);
  return result;
}
