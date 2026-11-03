"""Bounded startup/termination race diagnostic, preserving first failing stderr."""
import sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_navigation_reuse/test'))
from test_process_cleanup import ProcessCleanupTests
for attempt in range(8):
 print('ATTEMPT',attempt+1,flush=True)
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ProcessCleanupTests('test_gateway_sigterm_has_normal_exit')]))
 if not result.wasSuccessful():sys.exit(1)
