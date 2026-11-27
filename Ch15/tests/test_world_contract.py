import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_simulation'

class WorldTests(unittest.TestCase):
    def test_cube(self):
        model=ET.parse(ROOT/'models/red_cube/model.sdf').getroot().find('model')
        world=ET.parse(ROOT/'worlds/fetch_carry.sdf').getroot().find('world')
        cube=world.find("model[@name='red_cube']")
        self.assertEqual(ET.tostring(model),ET.tostring(cube))
        link=cube.find('link'); pose=list(map(float,cube.findtext('pose').split()))
        self.assertAlmostEqual(pose[2],.225,places=6)
        self.assertAlmostEqual(float(link.findtext('inertial/mass')),.1,places=6)
        for k in ('ixx','iyy','izz'):
            self.assertAlmostEqual(float(link.findtext('inertial/inertia/'+k)),.1*(.05**2+.05**2)/12,places=6)
        for k in ('ixy','ixz','iyz'):
            self.assertEqual(float(link.findtext('inertial/inertia/'+k)),0)
        for k in ('collision','visual'):
            self.assertEqual(list(map(float,link.findtext(k+'/geometry/box/size').split())),[.05]*3)
        table=world.find("model[@name='table']")
        z=float(table.findtext('pose').split()[2]);h=float(table.findtext('link/collision/geometry/box/size').split()[2]);self.assertAlmostEqual(z+h/2,pose[2]-.025,places=6)

    def test_sensor_and_unique_models(self):
        world=ET.parse(ROOT/'worlds/fetch_carry.sdf').getroot().find('world')
        names=[x.get('name') for x in world.findall('model')];self.assertEqual(len(names),len(set(names)))
        sensors=world.findall('.//sensor');self.assertEqual(len(sensors),1)
        self.assertEqual(sensors[0].get('type'),'rgbd_camera')
        self.assertEqual(float(sensors[0].findtext('update_rate')),5.)

if __name__=='__main__': unittest.main()
