// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/control_clock_relay.hpp"
#include "integrated_robot_navigation_sensors/async_trace.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>

namespace {
void write_line(int descriptor,const std::string & line)
{
  size_t offset=0;
  while(offset<line.size()){
    const auto count=::write(descriptor,line.data()+offset,line.size()-offset);
    if(count<0 && errno==EINTR){continue;}
    if(count<=0){throw std::runtime_error("control clock trace write failed");}
    offset+=static_cast<size_t>(count);
  }
}
void writer_witness(const std::string & path,const nlohmann::json & state)
{
  if(path.empty()){return;}
  const int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
  if(fd<0){throw std::runtime_error("control clock writer witness open failed");}
  try{write_line(fd,state.dump()+"\n");}
  catch(...){::close(fd);throw;}
  if(::close(fd)!=0){throw std::runtime_error("control clock writer witness close failed");}
}
}

int main(int argc, char ** argv)
{
  int descriptor = -1;
  std::string witness;
  std::unique_ptr<integrated_robot_navigation_sensors::AsyncTrace> writer;
  try {
    rclcpp::init(argc, argv);
    const auto arguments = rclcpp::remove_ros_arguments(argc, argv);
    if (arguments.size() > 2) {throw std::invalid_argument("usage: control_clock_relay [NEW_TRACE.jsonl]");}
    if (arguments.size() == 2) {
      descriptor = ::open(arguments[1].c_str(), O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0600);
      if (descriptor < 0) {throw std::runtime_error(std::strerror(errno));}
      witness=arguments[1]+".writer.json";
    }
    writer=std::make_unique<integrated_robot_navigation_sensors::AsyncTrace>(
      [descriptor](const std::string & line){if(descriptor>=0){write_line(descriptor,line);}});
    int result;
    {
      auto relay = std::make_shared<integrated_robot_navigation_sensors::ControlClockRelay>(
        [&writer](const nlohmann::json & row){writer->submit(row);});
      rclcpp::spin(relay);
      relay->finish();
      result = relay->report().at("fault").get<std::string>().empty() ? 0 : 1;
    }  // block/finish callbacks BEFORE closing trace input
    writer->finish();  // drain and join BEFORE descriptor close; failure stays exit1
    writer_witness(witness,writer->report());
    if (descriptor >= 0 && ::close(descriptor) != 0) {throw std::runtime_error("control clock close failed");}
    descriptor = -1;
    rclcpp::shutdown();
    return result;
  } catch (const std::exception & error) {
    std::cerr << "control clock failure: " << error.what() << std::endl;
    if(writer){
      try{writer->finish();}catch(const std::exception & failure){std::cerr<<failure.what()<<std::endl;}
      try{writer_witness(witness,writer->report());}catch(const std::exception & failure){std::cerr<<failure.what()<<std::endl;}
    }
    if (descriptor >= 0) {::close(descriptor);}
    rclcpp::shutdown();
    return 1;
  }
}
