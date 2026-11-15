#!/usr/bin/env python3
"""Original SDF semantics unchanged except DART-6.13 lower position limits."""
import sys, unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_g04b_dart_limit_margin import apply_test_only_dart_margin

NAMES=("joint1","joint2","joint3","joint4","joint_wrist")
def source():
    root=ET.Element("sdf",{"version":"1.10"})
    model=ET.SubElement(root,"model",{"name":"my_robot"})
    ET.SubElement(model,"static").text="false"
    ET.SubElement(model,"link",{"name":"link_wrist"})
    ET.SubElement(model,"link",{"name":"finger1"})
    ET.SubElement(model,"link",{"name":"finger2"})
    for name in NAMES:
        j=ET.SubElement(model,"joint",{"name":name,"type":"revolute"})
        ET.SubElement(j,"parent").text="base_link"
        ET.SubElement(j,"child").text="link_wrist"
    for name,axis in [("joint_finger1","1 0 0"),("joint_finger2","-1 0 0")]:
        j=ET.SubElement(model,"joint",{"name":name,"type":"prismatic"})
        ET.SubElement(j,"parent").text="link_wrist"
        ET.SubElement(j,"child").text=name.replace("joint_","")
        a=ET.SubElement(j,"axis"); ET.SubElement(a,"xyz").text=axis
        lim=ET.SubElement(a,"limit")
        ET.SubElement(lim,"lower").text="0"
        ET.SubElement(lim,"upper").text="0.025"
        ET.SubElement(lim,"effort").text="20"
        ET.SubElement(lim,"velocity").text="0.2"
    j=ET.SubElement(model,"joint",{
       "name":"g04b_test_only_world_to_base_fixed","type":"fixed"})
    ET.SubElement(j,"parent").text="world"
    ET.SubElement(j,"child").text="base_link"
    return ET.tostring(root,encoding="unicode")

class TestDartLowerBoundCandidate(unittest.TestCase):
 def test_only_two_original_physics_lower_limits_change(self):
    src=source()
    result,receipt=apply_test_only_dart_margin(src)
    self.assertNotEqual(src,result)
    self.assertEqual(len(receipt["changed_joint_fields"]),2)
    self.assertEqual(receipt["sdf_physical_lower_m"],-.001)
    self.assertEqual(receipt["original_urdf_and_controller_command_lower_m"],0.)
    x=ET.fromstring(result)
    for name in ["joint_finger1","joint_finger2"]:
        self.assertEqual(float(x.findtext(".//joint[@name='"+name+"']/axis/limit/lower")),-.001)
        self.assertEqual(float(x.findtext(".//joint[@name='"+name+"']/axis/limit/upper")),.025)
    self.assertEqual(len(x.findall(".//joint")),8)
    self.assertFalse(receipt["real_rod_attach_or_teleport"])
    self.assertEqual(receipt["G04B"],"BLOCKED_PENDING_NATIVE_REAL_GAZEBO")
 def test_missing_joint_rejected(self):
    root=ET.fromstring(source())
    root.find("model").remove(root.find("./model/joint[@name='joint_finger2']"))
    with self.assertRaises(ValueError):
        apply_test_only_dart_margin(ET.tostring(root,encoding="unicode"))
 def test_source_joint_axis_change_rejected(self):
    root=ET.fromstring(source())
    root.find("./model/joint[@name='joint_finger1']/axis/xyz").text="-1 0 0"
    with self.assertRaises(ValueError):
        apply_test_only_dart_margin(ET.tostring(root,encoding="unicode"))
 def test_original_upper_or_lower_modified_rejected(self):
    for field,value in [("lower","-0.001"),("upper","0.1")]:
        root=ET.fromstring(source())
        root.find("./model/joint[@name='joint_finger2']/axis/limit/"+field).text=value
        with self.assertRaises(ValueError):
            apply_test_only_dart_margin(ET.tostring(root,encoding="unicode"))
 def test_source_cannot_already_have_anchor_added_twice(self):
    root=ET.fromstring(source())
    extra=ET.fromstring(ET.tostring(root.find("./model/joint[@name='g04b_test_only_world_to_base_fixed']")))
    root.find("model").append(extra)
    with self.assertRaises(ValueError):
        apply_test_only_dart_margin(ET.tostring(root,encoding="unicode"))
 def test_robot_must_remain_dynamic(self):
    root=ET.fromstring(source())
    root.find("./model/static").text="true"
    with self.assertRaises(ValueError):
        apply_test_only_dart_margin(ET.tostring(root,encoding="unicode"))

if __name__=="__main__":unittest.main()
