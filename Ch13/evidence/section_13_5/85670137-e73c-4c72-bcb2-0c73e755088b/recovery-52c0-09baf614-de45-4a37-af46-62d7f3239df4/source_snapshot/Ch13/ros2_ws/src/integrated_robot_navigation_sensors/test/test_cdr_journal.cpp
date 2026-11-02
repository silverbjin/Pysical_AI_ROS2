// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <unistd.h>
#include <filesystem>
#include "integrated_robot_navigation_sensors/cdr_journal.hpp"
using integrated_robot_navigation_sensors::CdrJournal;
namespace {
std::string path(const char * name) {
  static unsigned counter=0;
  return ::testing::TempDir()+"ch13-cdr-"+std::to_string(getpid())+"-"+
    std::to_string(++counter)+name;
}
}
TEST(CdrJournal, DrainAndFooterAreJoinedBeforeNormalClose) {
  const auto file=path(".cdr");
  CdrJournal journal(file);
  for (unsigned i=0;i<100;++i) {
    ASSERT_TRUE(journal.submit({{"kind","frame"},{"ros_ns",i},{"wall_ns",i},{"stage","stand"}}));
  }
  journal.close();const auto report=journal.report();
  EXPECT_EQ(report.at("submitted"),101);EXPECT_EQ(report.at("written"),101);
  EXPECT_EQ(report.at("error"),"");EXPECT_EQ(report.at("joined"),true);
  EXPECT_FALSE(journal.submit({{"kind","frame"}}));
  EXPECT_GT(std::filesystem::file_size(file),100u);std::filesystem::remove(file);
}
TEST(CdrJournal, CapacityViolationIsStickyAndCannotBecomeSuccessAfterDrain) {
  const auto file=path(".cdr");
  CdrJournal journal(file,256,100);
  EXPECT_FALSE(journal.submit({{"kind","frame"}}));
  journal.close();
  EXPECT_NE(journal.report().at("error"),"");
  EXPECT_EQ(journal.report().at("joined"),true);std::filesystem::remove(file);
}
TEST(CdrJournal, ExistingEvidenceIsNeverOverwritten) {
  const auto file=path(".cdr");
  CdrJournal journal(file);journal.close();
  EXPECT_THROW(CdrJournal duplicate(file),std::runtime_error);
  std::filesystem::remove(file);
}
