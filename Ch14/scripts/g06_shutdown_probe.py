"""Short installed sim launch; one semantic witness, no hot-swap or benchmark repeat."""
import argparse,json,os,subprocess,signal
from pathlib import Path
import rclpy
from g03_gazebo_witness import Witness
from g06_shutdown_sequence import stop_launch
def main():
    p=argparse.ArgumentParser();p.add_argument("--onnx",type=Path,required=True);p.add_argument("--sha256",required=True);p.add_argument("--assets",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    cmd=["ros2","launch","ch14_ai_perception","robot_ai_system.launch.py","profile:=sim","assets:="+str(a.assets),"model_path:="+str(a.onnx),"model_sha256:="+a.sha256]
    log=a.out/"shutdown-launch.log"
    with log.open("w") as f:
        proc=subprocess.Popen(cmd,cwd="/tmp",stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        rclpy.init();w=Witness(a.out)
        try:
            rows=w.collect(3,timeout=40)
            (a.out/"shutdown-witness.json").write_text(json.dumps(rows,indent=2)+"\n")
            assert len(rows)==3 and all(x["status"]=="PASS" for x in rows)
        finally:
            w.destroy_node();rclpy.try_shutdown()
            stop_launch(proc,log,a.out,os.environ.copy())
if __name__=="__main__":main()
