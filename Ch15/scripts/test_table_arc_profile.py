import math,unittest
from arc_straight_profile import arc_point,arc_command,ANGLE
from table_arc_profile import table_arc_command
class TestTableArc(unittest.TestCase):
    def test_cross_only(self):
        th=.8;x,y=arc_point(th);p=(x-.02*math.sin(th),y-.02*math.cos(th),-th)
        old=arc_command(p);new=table_arc_command(p)
        self.assertGreater(new[0],old[0]);self.assertEqual(new[1],old[1])
        self.assertLessEqual(new[0],.018);self.assertGreaterEqual(new[1],-.10)
        self.assertLessEqual(new[1],-.07)
        nominal=(x,y,-th);self.assertEqual(table_arc_command(nominal),arc_command(nominal))
    def test_bounds(self):
        self.assertIsNone(table_arc_command((math.nan,0,0)))
        self.assertIsNone(table_arc_command((.06,0,0)))
        self.assertEqual(table_arc_command((*arc_point(ANGLE),-ANGLE)),(0.,0.))
if __name__=='__main__':unittest.main()
