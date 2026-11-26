"""Actual ROS services, model generation, threshold snapshots and installed replay launch."""
import argparse,json,math,os,signal,subprocess,time
from pathlib import Path
import cv2
import rclpy
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
from rcl_interfaces.srv import SetParametersAtomically,GetParameters
from ch14_ai_interfaces.srv import SwapModel
from ch14_ai_common.yolo_lab import iou
from g03_ros_dds_probe import Probe,hit

NODE="/yolo_detector_node"
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")
def parse(log,tag):
    return [json.loads(l.split(tag+" ",1)[1]) for l in log.read_text().splitlines() if tag+" " in l]
def until(probe,predicate,seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        probe.spin(.02)
        v=predicate()
        if v:return v
    raise AssertionError("condition timeout")
def call(probe,client,req):
    future=client.call_async(req)
    until(probe,lambda:future.done())
    return future.result()
def param(name,value,kind=ParameterType.PARAMETER_DOUBLE):
    x=ParameterValue(type=kind)
    if kind==ParameterType.PARAMETER_DOUBLE:x.double_value=value
    elif kind==ParameterType.PARAMETER_INTEGER:x.integer_value=value
    elif kind==ParameterType.PARAMETER_BOOL:x.bool_value=value
    elif kind==ParameterType.PARAMETER_STRING:x.string_value=value
    return Parameter(name=name,value=x)

def main():
    p=argparse.ArgumentParser();p.add_argument("--registry",type=Path,required=True);p.add_argument("--image",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    reg=json.loads(a.registry.read_text());models={m["model_id"]:m for m in reg["models"]};n=models["yolov8n"];s=models["yolov8s"]
    path=a.registry.parent/n["file"];spath=a.registry.parent/s["file"]
    from ament_index_python.packages import get_package_share_directory
    import yaml
    # Custom YAML differs from default, CLI overrides confidence only.
    share=Path(get_package_share_directory("ch14_ai_perception"))
    config=yaml.safe_load((share/"config/params_replay.yaml").read_text())
    config["/**"]["ros__parameters"].update(confidence_threshold=.6,iou_threshold=.4)
    cfg=Path("/tmp/g04-replay-override.yaml");cfg.write_text(yaml.safe_dump(config))
    base=["ros2","launch","ch14_ai_perception","robot_ai_system.launch.py","profile:=replay",
          "config:="+str(cfg),"model_path:="+str(path),"model_sha256:="+n["sha256"],
          "model_registry:="+str(a.registry),"sensor_reliability:=reliable","trace_inputs:=true","delay_ms:=60.0"]
    invalid=[base+["confidence_threshold:=1.1"],[v if not v.startswith("model_path:=") else "model_path:=/tmp/nonexistent.onnx" for v in base]]
    for idx,cmd in enumerate(invalid):
        r=subprocess.run(cmd,cwd="/tmp",capture_output=True,text=True,timeout=20)
        (a.out/f"invalid_start_{idx}.log").write_text(r.stdout+r.stderr)
        assert r.returncode!=0 and "CH14_READY" not in r.stdout+r.stderr
    log=a.out/"replay-launch.log";f=log.open("w")
    proc=subprocess.Popen(base+["confidence_threshold:=0.5"],cwd="/tmp",stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();probe=Probe(cv2.imread(str(a.image)),a.out,reliable=True);result={"invalid_startup":2};events=[]
    try:
        probe.wait_ready(proc)
        setter=probe.create_client(SetParametersAtomically,NODE+"/set_parameters_atomically")
        getter=probe.create_client(GetParameters,NODE+"/get_parameters")
        swap=probe.create_client(SwapModel,"/ch14/swap_model")
        for c in (setter,getter,swap):assert c.wait_for_service(timeout_sec=5)
        def get():
            names=["confidence_threshold","iou_threshold"]
            v=call(probe,getter,GetParameters.Request(names=names)).values
            return [x.double_value for x in v]
        def set_(items,ok):
            r=call(probe,setter,SetParametersAtomically.Request(parameters=items)).result
            events.append(dict(test="parameter",names=[i.name for i in items],success=r.successful,reason=r.reason))
            assert r.successful==ok,(r.reason,ok)
        assert get()==[.5,.4]
        cli=subprocess.run(["ros2","param","get",NODE,"iou_threshold"],cwd="/tmp",capture_output=True,text=True,timeout=15)
        (a.out/"cli-param-get.log").write_text(cli.stdout+cli.stderr)
        assert cli.returncode==0 and "0.4" in cli.stdout
        result["precedence"]={"yaml_confidence":.6,"cli_confidence":.5,"yaml_iou":.4,"actual":get()}
        for v in (0.,1.):
            set_([param("confidence_threshold",v),param("iou_threshold",v)],True);assert get()==[v,v]
        set_([param("confidence_threshold",.5),param("iou_threshold",.45)],True)
        for v in (-.01,1.01,float("nan"),float("inf")):
            set_([param("confidence_threshold",.7),param("iou_threshold",v)],False);assert get()==[.5,.45]
        set_([param("confidence_threshold",1,ParameterType.PARAMETER_INTEGER)],False)
        for name,val,kind in [("model_path","/tmp/other.onnx",ParameterType.PARAMETER_STRING),("backend","openvino",ParameterType.PARAMETER_STRING),
                             ("use_sim_time",True,ParameterType.PARAMETER_BOOL),("input_topic","/other",ParameterType.PARAMETER_STRING),("max_age_sec",.2,ParameterType.PARAMETER_DOUBLE)]:
            set_([param("confidence_threshold",.8),param(name,val,kind)],False);assert get()==[.5,.45]
        def send_result(expect_hit):
            stamp=probe.send();row=until(probe,lambda:next((d for d in probe.ds if d["stamp"]==stamp),None),3)
            assert hit(row)==expect_hit
            if not expect_hit:assert not row["boxes"]
            return stamp
        low=send_result(True)
        set_([param("confidence_threshold",1.)],True)
        high=send_result(False)
        set_([param("confidence_threshold",.5)],True)
        restored=send_result(True)
        result["threshold_frames"]=[low,high,restored]
        # Same image, change committed while old frame is being delayed. Capture input trace before update.
        inflight=probe.send()
        until(probe,lambda:any(r["stamp"]==inflight for r in parse(log,"CH14_INPUT")),2)
        set_([param("confidence_threshold",1.)],True)
        oldrow=until(probe,lambda:next((d for d in probe.ds if d["stamp"]==inflight),None),3)
        assert hit(oldrow)
        newrow=send_result(False)
        set_([param("confidence_threshold",.5)],True)
        result["inflight_threshold"]=[inflight,newrow]
        def request(i):
            r=call(probe,swap,SwapModel.Request(model_id=i))
            events.append(dict(test="swap",model_id=i,accepted=r.accepted,request_id=r.request_id,reason=r.reason))
            return r
        def terminal(r,state):
            assert r.accepted and r.request_id
            row=until(probe,lambda:next((x for x in parse(log,"CH14_SWAP") if x.get("request_id")==r.request_id and x["state"] in ("FAILED","SUCCEEDED","CANCELLED")),None),15)
            assert row["state"]==state,row
            return row
        for bad in ("../unsafe","yolov8n"):
            r=request(bad);assert not r.accepted and not r.request_id
        backup=spath.with_suffix(".saved")
        for kind in ("missing","corrupt"):
            spath.rename(backup)
            try:
                if kind=="corrupt":spath.write_bytes(b"corrupted model")
                row=terminal(request("yolov8s"),"FAILED")
                assert row["active_id"]=="yolov8n" and row["active_sha256"]==n["sha256"] and row["generation"]==0
                send_result(True)
                result[kind]=row
            finally:
                if spath.exists():spath.unlink()
                backup.rename(spath)
        # Keep publishing during actual candidate load; simultaneous requests must not start two loaders.
        probe.send()
        f1=swap.call_async(SwapModel.Request(model_id="yolov8s"))
        f2=swap.call_async(SwapModel.Request(model_id="yolov8s"))
        until(probe,lambda:f1.done() and f2.done())
        rr=[f1.result(),f2.result()]
        assert sum(x.accepted for x in rr)==1 and any(x.reason=="BUSY" for x in rr)
        accepted=next(x for x in rr if x.accepted)
        end=time.monotonic()+15;row=None
        while time.monotonic()<end:
            probe.send();probe.spin(.15)
            row=next((x for x in parse(log,"CH14_SWAP") if x.get("request_id")==accepted.request_id and x["state"] in ("FAILED","SUCCEEDED")),None)
            if row:break
        assert row and row["state"]=="SUCCEEDED" and row["generation"]==1 and row["active_sha256"]==s["sha256"],row
        probe.spin(.35)
        post=send_result(True)
        result["success"]=row;result["busy_rejected"]=True
        emits=parse(log,"CH14_EMIT")
        for stamp_,v in [(low,.5),(high,1.),(restored,.5),(inflight,.5),(newrow,1.)]:
            assert next(e for e in emits if e["stamp"]==stamp_)["confidence_threshold"]==v
        assert next(e for e in emits if e["stamp"]==post)["generation"]==1
        assert all(e["generation"]==1 for e in emits if e["wall_ns"]>row["wall_ns"])
        assert all(0<=e["oldest_age_ms"]<=300 for e in emits)
        started=next(x for x in parse(log,"CH14_SWAP") if x["request_id"]==accepted.request_id and x["state"]=="LOADING")
        old_emits=[e for e in emits if e["generation"]==0 and started["wall_ns"]<=e["wall_ns"]<row["wall_ns"]]
        assert old_emits,"no old-model emission while candidate loading"
        before=max(e["wall_ns"] for e in emits if e["generation"]==0)
        after=min(e["wall_ns"] for e in emits if e["generation"]==1)
        result.update(old_emits_during_load=len(old_emits),output_gap_ms=(after-before)/1e6,emits=emits,
                      heartbeat_max_ms=max(h["heartbeat_interval_ms"] for h in probe.hs if h["heartbeat_interval_ms"] is not None),
                      status="PASS")
    finally:
        if proc.poll() is None:proc.send_signal(signal.SIGINT)
        try:rc=proc.wait(timeout=15)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=-9
        f.close();probe.dump("g04-replay-dds")
        result["launch_exit"]=rc;result["events"]=events
        text=log.read_text();result["clean_shutdown"]="CH14_SHUTDOWN" in text and '"worker_joined": true' in text
        dump(a.out/"g04-replay-result.json",result)
        probe.destroy_node();rclpy.try_shutdown()
        assert rc==0 and result["clean_shutdown"],"launch/worker unclean shutdown"
if __name__=="__main__":main()
