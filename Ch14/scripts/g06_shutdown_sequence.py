"""Owned launch shutdown, consumer first; server service ACK is not exit proof."""
import json,os,re,signal,subprocess,time
from pathlib import Path
import psutil

NAMES=("detector_node","static_transform_publisher","parameter_bridge","gz")
def stop_launch(proc,log,out,env=None):
    events=[];children={};result={"status":"FAIL","events":events,"processes":{}}
    def note(stage,**extra):
        events.append(dict(stage=stage,wall_ns=time.monotonic_ns(),**extra))
        (out/"shutdown-sequence.json").write_text(json.dumps(result,indent=2)+"\n")
    def read():return log.read_text(errors="replace")
    def wait_for(predicate,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():return True
            time.sleep(.05)
        return bool(predicate())
    def clean(name):
        pid=children[name].pid
        return bool(re.search(r"\["+re.escape(name)+r"-\d+\]: process has finished cleanly \[pid "+str(pid)+r"\]",read()))
    def signal_child(name,sig):
        p=children[name]
        if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE:p.send_signal(sig)
        note("signal",name=name,pid=p.pid,signal=sig.name)
    def snapshot():
        snap={}
        for name,p in children.items():
            try:
                snap[name]={"pid":p.pid,"status":p.status(),"threads":[dict(tid=t.id,user=t.user_time,system=t.system_time,wchan=(Path(f"/proc/{p.pid}/task/{t.id}/wchan").read_text().strip() if Path(f"/proc/{p.pid}/task/{t.id}/wchan").exists() else None)) for t in p.threads()]}
            except (OSError,psutil.Error) as e:snap[name]={"error":str(e)}
        return snap
    try:
        parent=psutil.Process(proc.pid)
        owned={p.pid:p for p in parent.children(recursive=True)}
        for name in NAMES:
            match=re.search(r"\["+re.escape(name)+r"-\d+\]: process started with pid \[(\d+)\]",read())
            if not match or int(match[1]) not in owned:raise RuntimeError("missing owned child "+name)
            children[name]=owned[int(match[1])]
        note("owned",pids={k:v.pid for k,v in children.items()})
        for name in NAMES[:-1]:signal_child(name,signal.SIGINT)
        if not wait_for(lambda:all(clean(n) for n in NAMES[:-1]),8):raise RuntimeError("consumer exit timeout")
        note("consumers_clean",worker_joined='"worker_joined": true' in read())
        if '"worker_joined": true' not in read():raise RuntimeError("worker not joined")
        stop=subprocess.run(["gz","service","-s","/server_control","--reqtype","gz.msgs.ServerControl","--reptype","gz.msgs.Boolean","--timeout","1500","--req","stop: true"],env=env,capture_output=True,text=True,timeout=5)
        (out/"server-stop.log").write_text(stop.stdout+stop.stderr)
        note("server_ack",returncode=stop.returncode,reply=stop.stdout.strip())
        if stop.returncode!=0 or "data: true" not in stop.stdout:raise RuntimeError("stop not acknowledged")
        if not wait_for(lambda:clean("gz"),8):
            note("server_ack_without_exit",snapshot=snapshot())
            signal_child("gz",signal.SIGINT)
            if not wait_for(lambda:clean("gz"),5):
                note("server_exit_timeout",snapshot=snapshot())
                raise RuntimeError("server did not exit after ACK and bounded SIGINT")
        note("server_clean")
        if proc.poll() is None:proc.send_signal(signal.SIGINT)
        rc=proc.wait(timeout=8)
        result["processes"]={n:{"pid":children[n].pid,"clean_exit":clean(n)} for n in NAMES}
        result["launch_exit"]=rc
        if rc!=0 or not all(v["clean_exit"] for v in result["processes"].values()) or "process has died" in read():raise RuntimeError("unclean launch")
        result["status"]="PASS";note("complete")
        return result
    except Exception as e:
        result["reason"]=str(e);note("failure",snapshot=snapshot())
        raise
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:proc.wait(timeout=18)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();note("forced_cleanup")
