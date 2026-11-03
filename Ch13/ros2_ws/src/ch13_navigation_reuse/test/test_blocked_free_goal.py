"""Blocked means a free destination separated by a wall, not an occupied goal."""
import unittest
from ch13_navigation_reuse.scene import layout
class BlockedGoalTests(unittest.TestCase):
 def test_blocked_free_goal_has_no_connected_free_path(self):
  scene=layout('blocked')
  def occupied(x,y):
   px=-2+(x+.5)*.05;py=-2.5+(y+.5)*.05
   return any(abs(px-p[0])<=z[0]+.025 and abs(py-p[1])<=z[1]+.025 for _,p,z in scene)
  start=(40,50);goal=(85,50);self.assertFalse(occupied(*goal));todo=[start];seen={start}
  while todo:
   x,y=todo.pop()
   for xy in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
    if 0<=xy[0]<120 and 0<=xy[1]<100 and xy not in seen and not occupied(*xy):seen.add(xy);todo.append(xy)
  self.assertNotIn(goal,seen)
