import math,unittest
from table_approach_contract import *

class Contract(unittest.TestCase):
    def test_absolute_goal(self):
        for g in [(2.2,1,0),(1,2,2.9),(-3,4,-2.8)]:
            got=world(final_target(),entry_for(g))
            self.assertLess(math.dist(g[:2],got[:2]),1e-12)
            self.assertLess(abs(wrap(g[2]-got[2])),1e-12)
    def test_entry_not_reanchored(self):
        e=entry_for((2.2,1,0));self.assertTrue(entry_ready(e,e))
        self.assertFalse(entry_ready((e[0]+.031,e[1],e[2]),e))
        self.assertFalse(entry_ready((e[0],e[1],e[2]+.061),e))
    def test_reject_invalid(self):
        with self.assertRaises(ValueError):entry_for((math.nan,0,0))
        with self.assertRaises(ValueError):route((0,0,0),(2.2,1,0))
    def test_route_continuity(self):
        g=(2.2,1,0);e=entry_for(g);s=(e[0]-math.cos(e[2]),e[1]-math.sin(e[2]),.75)
        r=route(s,g);self.assertEqual(r['travel'][-1],e)
        self.assertLess(math.dist(r['arc'][0][:2],e[:2]),1e-12)
        self.assertLess(math.dist(r['straight'][-1][:2],g[:2]),1e-12)
        for key in ('initial_turn','travel','arc','straight'):
            for a,b in zip(r[key],r[key][1:]):
                self.assertLessEqual(math.dist(a[:2],b[:2]),.005000001)
                self.assertLessEqual(abs(wrap(b[2]-a[2])),math.radians(1)+1e-9)
    def test_compensated_arc_preserves_final_goal(self):
        for g in [(2.2,1,0),(1,2,2.9),(-3,4,-2.8)]:
            e=entry_for(g);s=(e[0]-1.2*math.cos(e[2]),e[1]-1.2*math.sin(e[2]),e[2])
            r=route(s,g,arc_bias_m=.02)
            self.assertAlmostEqual(r['entry'][0]-e[0],-.02*math.sin(g[2]))
            self.assertAlmostEqual(r['entry'][1]-e[1],.02*math.cos(g[2]))
            self.assertEqual(r['straight_reference_entry'],e)
            self.assertLess(math.dist(world(final_target(),e)[:2],g[:2]),1e-12)
            self.assertLess(math.dist(r['straight'][-1][:2],g[:2]),1e-12)
            self.assertLess(math.dist(r['arc'][-1][:2],r['straight'][0][:2]),1e-12)
        for bias in (-.001,.026,math.nan):
            with self.assertRaises(ValueError):route(s,g,arc_bias_m=bias)
    def test_handoff_negative(self):
        args=dict(goal_terminal=4,goal_active=False,stationary=True,boundary_phase='IDLE',entry_ok=True,chain_ok=True,fault=False)
        for k,v in dict(goal_terminal=5,goal_active=True,stationary=False,boundary_phase='ACTIVE',entry_ok=False,chain_ok=False,fault=True).items():
            h=Handoff()
            with self.assertRaises(RuntimeError):h.switch(**{**args,k:v})
            self.assertEqual(h.owner,'NAV2')
        h=Handoff();h.switch(**args);self.assertEqual(h.owner,'V3')
        with self.assertRaises(RuntimeError):h.switch(**args)
if __name__=='__main__':unittest.main(verbosity=2)
