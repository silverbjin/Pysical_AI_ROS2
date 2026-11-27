import unittest
from table_l2_contract import TOPICS,bag_checks,goal_audit
class Contracts(unittest.TestCase):
    def test_bag_positive(self):
        c={x:1 for x in TOPICS}
        self.assertTrue(all(bag_checks(c,c,[10],[11],[12],TOPICS).values()))
    def test_bag_negative(self):
        c={x:1 for x in TOPICS}
        for args in [(c,c,[10],[9],[12],TOPICS),(c,c,[10],[11],[],TOPICS),(c,c,[10,11],[12],[13],TOPICS),(c,c,[10],[11],[12],TOPICS[:-1]),(c,{**c,'extra':1},[10],[11],[12],TOPICS)]:
            self.assertFalse(all(bag_checks(*args).values()))
    def test_goal_terminal(self):
        r=goal_audit([dict(goal_id='a'*32,terminal=4),dict(goal_id='b'*32,terminal=4)])
        self.assertEqual(r['pending'],0);self.assertEqual(r['errors'],[]);self.assertEqual(r['terminals'],[4,4])
    def test_goal_negative(self):
        self.assertEqual(goal_audit([dict(goal_id='a'*32)])['pending'],1)
        self.assertTrue(goal_audit([dict(goal_id='a'*32,terminal=4),dict(goal_id='a'*32,terminal=4)])['errors'])
if __name__=='__main__':unittest.main()
