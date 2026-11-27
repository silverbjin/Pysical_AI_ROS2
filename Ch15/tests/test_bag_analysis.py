import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from analyze_mission import analyze,energy_j
def fixture():
    base=dict(mission_id='m',epoch=0,source='MOCK',producer='ch15_mission_executor')
    events=[]
    for i,(name,rid,uid,detail) in enumerate([('START','','',{}),('GOAL_SENT','r','',{'requested_uuid':'a'*32}),('GOAL_ACCEPTED','r','a'*32,{}),('GOAL_TERMINAL','r','a'*32,{'status':4}),('END','','',{'state':'COMPLETED','all_terminal':True,'mock_mission_success':True,'full_mission_success':False})],1):
        events.append(dict(base,event=name,request_id=rid,goal_uuid=uid,detail=detail,event_seq=i,record_ns=1000000000*i,ros_ns=1000000000*i,steady_ns=1000000000*i))
    statuses=[dict(mission_id='m',epoch=0,source='MOCK',profile='mock',full_mission_success=False,state='COMPLETED',record_ns=5000000000,ros_ns=5000000000)]
    return events,statuses
class TestAnalysis(unittest.TestCase):
    def test_elapsed(self):
        e,s=fixture();m=analyze(e,s);self.assertAlmostEqual(m['elapsed_steady_s'],4,places=3);self.assertIsNone(m['energy_j'])
    def test_negatives(self):
        for key,value,index in [('event_seq',1,1),('event_seq',8,2),('mission_id','other',2),('ros_ns',1,2),('goal_uuid','b'*32,3),('source','PHYSICAL',2)]:
            e,s=fixture();e[index][key]=value
            with self.assertRaises(ValueError):analyze(e,s)
        e,s=fixture()
        with self.assertRaises(ValueError):analyze(e[:-1],s)
    def test_energy(self):
        self.assertAlmostEqual(energy_j([(0,[2],[3]),(1000000000,[2],[3])]),6,places=6)
        self.assertIsNone(energy_j([(0,[],[3]),(1000000000,[2],[3])]))
        self.assertIsNone(energy_j([(0,[2],[]),(1000000000,[2],[3])]))
if __name__=='__main__':unittest.main()
