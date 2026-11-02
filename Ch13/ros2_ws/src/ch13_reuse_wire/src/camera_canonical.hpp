// camera1: little-endian semantic fields, without unspecified CDR padding.
#pragma once
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <std_msgs/msg/string.hpp>
#include <cstring>
#include <stdexcept>
namespace camera1 {
using Bytes=std::vector<uint8_t>;
inline void u32(Bytes& b,uint32_t v){for(int i=0;i<4;++i)b.push_back(uint8_t(v>>(8*i)));}
inline void f64(Bytes& b,double v){uint64_t bits;std::memcpy(&bits,&v,8);for(int i=0;i<8;++i)b.push_back(uint8_t(bits>>(8*i)));}
inline void str(Bytes& b,const std::string& s){if(s.size()>2048)throw std::length_error("camera string");u32(b,s.size());b.insert(b.end(),s.begin(),s.end());}
inline void header(Bytes& b,const std_msgs::msg::Header& h){u32(b,uint32_t(h.stamp.sec));u32(b,h.stamp.nanosec);str(b,h.frame_id);}
inline Bytes fields(const sensor_msgs::msg::Image& m){
 if(m.data.size()>524288)throw std::length_error("camera image");Bytes b;b.reserve(m.data.size()+256);header(b,m.header);u32(b,m.height);u32(b,m.width);str(b,m.encoding);b.push_back(m.is_bigendian);u32(b,m.step);u32(b,m.data.size());b.insert(b.end(),m.data.begin(),m.data.end());return b;
}
inline Bytes fields(const sensor_msgs::msg::CameraInfo& m){
 if(m.d.size()>64)throw std::length_error("camera calibration");Bytes b;header(b,m.header);u32(b,m.height);u32(b,m.width);str(b,m.distortion_model);u32(b,m.d.size());for(auto v:m.d)f64(b,v);for(auto v:m.k)f64(b,v);for(auto v:m.r)f64(b,v);for(auto v:m.p)f64(b,v);u32(b,m.binning_x);u32(b,m.binning_y);u32(b,m.roi.x_offset);u32(b,m.roi.y_offset);u32(b,m.roi.height);u32(b,m.roi.width);b.push_back(m.roi.do_rectify?1:0);return b;
}
inline Bytes fields(const std_msgs::msg::String& m){Bytes b;str(b,m.data);return b;}
}
