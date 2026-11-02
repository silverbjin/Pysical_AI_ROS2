"""Reproduce the full-chain safe-header rollback with a delayed native zero."""
import unittest,time
class SafeHandoffTests(unittest.TestCase):
 def test_delayed_raw_zero_arm_never_regresses_safe_header(self):
  from test_ros_wire import WireTests
  from ch13_navigation_reuse.command_gateway import ns
  fixture=WireTests('test_live_raw_to_safe_requires_explicit_arm');fixture.raw_delay_ns=100_000_000;fixture.setUp()
  try:
   fixture.assertTrue(fixture.until(lambda:len(fixture.outputs)>5));fixture.arm();fixture.assertTrue(fixture.until(lambda:fixture.status.get('mode')=='ARMED'));time.sleep(.15)
   stamps=[ns(m.header.stamp) for m in fixture.outputs];self.assertTrue(all(b>=a for a,b in zip(stamps,stamps[1:])),str(stamps));self.assertEqual(fixture.status.get('fault'),'')
  finally:fixture.tearDown()
