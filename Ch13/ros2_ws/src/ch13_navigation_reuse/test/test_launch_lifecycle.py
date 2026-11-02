"""Real launch early-failure cleanup; no MuJoCo model is loaded."""
import importlib.util,os,re,signal,subprocess,sys,tempfile,unittest
from pathlib import Path
ROS=importlib.util.find_spec('launch') is not None
@unittest.skipUnless(ROS,'requires Jazzy launch')
class LaunchLifecycleTests(unittest.TestCase):
 def test_platform_exit_ends_owned_launch_group(self):
  root=Path(__file__).resolve().parents[5]
  source=root/'Ch13/ros2_ws/src/ch13_navigation_reuse/launch/platform.launch.py'
  with tempfile.TemporaryDirectory(prefix='ch13_r2_launch_') as temp:
   report=Path(temp)/'engine.json'
   command=['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch',str(source),'repo_root:='+str(Path(temp)/'missing_assets'),'report:='+str(report)]
   process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
   spontaneous=True
   try:output=process.communicate(timeout=6.)[0]
   except subprocess.TimeoutExpired:
    spontaneous=False;process.send_signal(signal.SIGINT)
    try:output=process.communicate(timeout=4.)[0]
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);output=process.communicate(timeout=3.)[0]
   self.assertTrue(spontaneous,'platform failure left launch group alive: '+output)
   self.assertTrue(report.is_file(),output)
   for pid in re.findall(r'process started with pid \[(\d+)\]',output):
    proc=Path('/proc')/pid/'cmdline'
    self.assertFalse(proc.exists() and proc.read_bytes(),'owned child remains: '+pid)
if __name__=='__main__':unittest.main()
