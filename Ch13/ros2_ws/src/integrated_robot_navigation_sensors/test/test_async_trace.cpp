// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include "integrated_robot_navigation_sensors/async_trace.hpp"
#include <chrono>
#include <future>
#include <mutex>
#include <vector>
using namespace std::chrono_literals;
using integrated_robot_navigation_sensors::AsyncTrace;

TEST(AsyncTrace, BlockedWriteDoesNotBlockClockProducerAndDrainsInOrder)
{
  std::promise<void> entered,release;auto permit=release.get_future().share();
  std::vector<std::string> written;
  AsyncTrace writer([&](const std::string & line) {
      if(written.empty()){entered.set_value();permit.wait();}written.push_back(line);
    },128,4096);
  writer.submit({{"sequence",0}});
  const auto ready=entered.get_future().wait_for(1s);
  if(ready!=std::future_status::ready){release.set_value();}
  ASSERT_EQ(ready,std::future_status::ready);
  const auto start=std::chrono::steady_clock::now();
  for(int i=1;i<30;++i){writer.submit({{"sequence",i}});}
  const auto elapsed=std::chrono::steady_clock::now()-start;
  release.set_value();writer.finish();
  EXPECT_LT(elapsed,50ms);ASSERT_EQ(written.size(),30u);
  for(size_t i=0;i<written.size();++i){EXPECT_EQ(nlohmann::json::parse(written[i]).at("sequence"),i);}
  auto state=writer.report();EXPECT_TRUE(state.at("joined"));EXPECT_TRUE(state.at("closed"));
  EXPECT_EQ(state.at("accepted"),30u);EXPECT_EQ(state.at("written"),30u);
  EXPECT_THROW(writer.submit({{"sequence",31}}),std::runtime_error);
}

TEST(AsyncTrace, QueueOverflowLatchesAndCannotSilentlyDropOrReopen)
{
  std::promise<void> entered,release;auto permit=release.get_future().share();
  size_t written=0;
  AsyncTrace writer([&](const std::string &) {
      if(written++==0){entered.set_value();permit.wait();}
    },3,4096);
  writer.submit({{"sequence",0}});
  const auto ready=entered.get_future().wait_for(1s);
  if(ready!=std::future_status::ready){release.set_value();}
  ASSERT_EQ(ready,std::future_status::ready);
  writer.submit({{"sequence",1}});writer.submit({{"sequence",2}});
  EXPECT_THROW(writer.submit({{"sequence",3}}),std::runtime_error);
  release.set_value();EXPECT_THROW(writer.finish(),std::runtime_error);
  EXPECT_EQ(written,3u);EXPECT_EQ(writer.report().at("error"),"trace_queue_capacity");
  EXPECT_TRUE(writer.report().at("joined"));
  EXPECT_THROW(writer.submit({{"sequence",4}}),std::runtime_error);
}

TEST(AsyncTrace, ByteBudgetAndWriterErrorsAreTerminalFailures)
{
  AsyncTrace small([](const std::string &){},4,8);
  EXPECT_THROW(small.submit({{"long","record"}}),std::runtime_error);
  EXPECT_THROW(small.finish(),std::runtime_error);
  EXPECT_EQ(small.report().at("error"),"trace_queue_bytes");
  AsyncTrace broken([](const std::string &){throw std::runtime_error("injected_disk_failure");},4,4096);
  broken.submit({{"sequence",0}});EXPECT_THROW(broken.finish(),std::runtime_error);
  EXPECT_TRUE(broken.report().at("joined"));EXPECT_EQ(broken.report().at("written"),0u);
  EXPECT_THROW(broken.submit({{"sequence",1}}),std::runtime_error);
}
