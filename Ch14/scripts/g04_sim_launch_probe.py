"""New T12 installed launch route; do not repeat historical G03 full L2 suite."""
import argparse,json,os,signal,subprocess
from pathlib import Path
import rclpy
from g03_gazebo_witness import Witness
def main():
    p=argparse.ArgumentParser();p.add_argument("--registry",type=Path,required=True);p.add_argument("--assets",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    n=json.loads(a.registry.read_text())["models"][0]
    cmd=["ros2","launch","ch14_ai_perception","robot_ai_system.launch.py","profile:=sim",
         "assets:="+str(a.assets),"model_path:="+str(a.registry.parent/n["file"]),
         "model_sha256:="+n["sha256"],"model_registry:="+str(a.registry),"trace_inputs:=true"]
    log=a.out/"sim-launch.log";f=log.open("w")
    proc=subprocess.Popen(cmd,cwd="/tmp",stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();w=Witness(a.out);result={}
    try:
        rows=w.collect(3,timeout=40)
        result.update(rows=rows,counts=w.count,clock_samples=len(w.clocks))
        assert len(rows)==3 and all(x["status"]=="PASS" for x in rows)
        assert w.clocks and any(h.get("model_id")=="yolov8n" and h.get("generation")==0 for h in w.hb)
        result["status"]="PASS"
    finally:
        if proc.poll() is None:
            # Ask actual server to stop, then signal only owned launch process.
            try:
                stop=subprocess.run(["gz","service","-s","/server_control","--reqtype","gz.msgs.ServerControl","--reptype","gz.msgs.Boolean","--timeout","1500","--req","stop: true"],capture_output=True,text=True,timeout=5)
                (a.out/"sim-stop.log").write_text(stop.stdout+stop.stderr)
            except subprocess.TimeoutExpired:result["server_stop_timeout"]=True
            proc.send_signal(signal.SIGINT)
        try:rc=proc.wait(timeout=18)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=-9
        f.close();text=log.read_text()
        result.update(launch_exit=rc,clean_worker="CH14_SHUTDOWN" in text and '"worker_joined": true' in text,heartbeats=w.hb)
        (a.out/"g04-sim-result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        w.destroy_node();rclpy.try_shutdown()
        assert rc==0 and result["clean_worker"] and "process has died" not in text,"launch unclean shutdown"
if __name__=="__main__":main()
