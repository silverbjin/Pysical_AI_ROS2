"""Actual fixed-scene CPU A/B/C; 60 wall seconds per profile, no fabricated D."""
import argparse,csv,json,math,os,platform,signal,subprocess,time
from pathlib import Path
from collections import Counter
import psutil,numpy as np
import rclpy
from ch14_performance_monitor.monitor_node import Monitor
from ch14_ai_common.benchmark import summarize
from ch14_ai_common.profiler import count_reconcile
from ch14_ai_common.yolo_lab import iou
from ch14_ai_common.backends import digest,CLASS_HASH

PROFILES={"A":("torch-cpu","sync"),"B":("ort","sync"),"C":("ort","async")}
PT_SHA="31e20dde3def09e2cf938c7be6fe23d9150bbbe503982af13345706515f2ef95"
GT=[306,66,367,438] # fixed G03 actual depth silhouette, unchanged world/mesh
STAGES=("receive_ms","queue_ms","preprocess_ms","inference_ms","postprocess_ms","result_wait_ms","publish_ms","pipeline_ms","age_ms","oldest_age_ms")
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+"\n")
def rows(log,tag):
    # launch prepends process label; JSON begins after exact trace marker.
    return [json.loads(x.split(tag+" ",1)[1]) for x in log.read_text().splitlines() if tag+" " in x]
def write_csv(path,items):
    if not items:return
    with path.open("w") as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader()
        w.writerows({k:json.dumps(v,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in items)
def resource(proc,seen):
    children=psutil.Process(proc.pid).children(recursive=True)
    by={"detector":[],"gazebo":[],"bridge":[],"tf":[],"other":[]}
    for p in children:
        try:
            cmd=" ".join(p.cmdline());name=p.name()
            if "detector_node" in cmd and "ros2 launch" not in cmd:key="detector"
            elif "gz sim" in cmd or "gz-sim" in cmd:key="gazebo"
            elif "parameter_bridge" in cmd:key="bridge"
            elif "static_transform_publisher" in cmd:key="tf"
            else:key="other"
            if p.pid not in seen:seen[p.pid]=p;p.cpu_percent(None);cpu=None
            else:cpu=seen[p.pid].cpu_percent(None)
            by[key].append((p.pid,cpu,p.memory_info().rss/2**20))
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    out={"wall_ns":time.monotonic_ns()}
    for k,items in by.items():
        out[k+"_pids"]=";".join(str(x[0]) for x in items)
        out[k+"_rss_mib"]=sum(x[2] for x in items)
        out[k+"_cpu_pct"]=sum(x[1] for x in items) if items and all(x[1] is not None for x in items) else None
    return out
def boxes_ok(a,b):
    remaining=list(b)
    for x in a:
        same=[(i,y) for i,y in enumerate(remaining) if y["label"]==x["label"]]
        if not same:return False
        j,y=max(same,key=lambda z:iou(x["xyxy"],z[1]["xyxy"]))
        if iou(x["xyxy"],y["xyxy"])<.95 or abs(x["score"]-y["score"])>.02:return False
        remaining.pop(j)
    return not remaining
def gt_ok(row):
    return any(b["label"]=="person" and iou(b["xyxy"],GT)>=.5 for b in row["boxes"])
def run_one(a,key,mode,backend):
    out=a.out/key;out.mkdir(exist_ok=False)
    pt=backend=="torch-cpu";model=a.pt if pt else a.onnx;sha=PT_SHA if pt else a.sha256
    cmd=["ros2","launch","ch14_ai_perception","robot_ai_system.launch.py","profile:=sim",
         "assets:="+str(a.assets),"model_path:="+str(model),"model_sha256:="+sha,
         "backend:="+backend,"mode:="+mode,"threads:=2","profile_timing:=true"]
    log=out/"launch.log";handle=log.open("w")
    # Different domain and transport partition for each new scene.
    env=dict(os.environ,GZ_PARTITION=os.environ["GZ_PARTITION"]+"_"+key)
    proc=subprocess.Popen(cmd,cwd="/tmp",stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    rclpy.init();m=Monitor();result={"profile":key,"backend":backend,"mode":mode,"command":cmd,"model_sha256":sha};resources=[];seen={}
    try:
        end=time.monotonic()+60
        while time.monotonic()<end:
            if proc.poll() is not None:raise RuntimeError("launch exited during warmup")
            m.spin(.1)
            if len(m.outputs)>=10 and m.heartbeats and m.first_clock and m.metrics["inference_latency"]>0:break
        else:raise RuntimeError("warmup 10 actual DDS outputs not reached")
        result["warmup_received"]=len(m.outputs)
        # Clear observer window, preserve source totals for separate shutdown reconciliation.
        resource(proc,seen);m.reset();t0=time.monotonic_ns();deadline=t0+60_000_000_000;next_sample=t0
        while time.monotonic_ns()<deadline:
            if proc.poll() is not None:raise RuntimeError("launch exited in measurement")
            m.spin(.025)
            if time.monotonic_ns()>=next_sample:
                resources.append(resource(proc,seen));next_sample+=1_000_000_000
        t1=time.monotonic_ns()
        result.update(window_start_ns=t0,window_end_ns=t1,wall_seconds=(t1-t0)/1e9)
        observed=m.snapshot();save(out/"observer.json",observed)
        write_csv(out/"resources.csv",resources)
        assert result["wall_seconds"]>=60 and observed["rtf"] is not None and observed["rtf"]>0 and observed["clock_resets"]==0
        assert observed["debug_invalid"]==0 and all(observed["debug_counts"].get(k,0)>0 for k in ("diagnostics","inference_latency","result_age","heartbeat_interval"))
    finally:
        if proc.poll() is None:
            try:
                stop=subprocess.run(["gz","service","-s","/server_control","--reqtype","gz.msgs.ServerControl","--reptype","gz.msgs.Boolean","--timeout","1500","--req","stop: true"],env=env,capture_output=True,text=True,timeout=5)
                (out/"server-stop.log").write_text(stop.stdout+stop.stderr)
            except subprocess.TimeoutExpired:result["server_stop_timeout"]=True
            if proc.poll() is None:proc.send_signal(signal.SIGINT)
        try:rc=proc.wait(timeout=18)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=-9
        handle.close();m.destroy_node();rclpy.try_shutdown()
        result["launch_exit"]=rc
        save(out/"result.json",result)
    assert rc==0
    shutdown=rows(log,"CH14_SHUTDOWN")
    assert len(shutdown)==1 and shutdown[0]["worker_joined"] and not shutdown[0]["slot"].get("worker_alive",False)
    assert "process has died" not in log.read_text()
    all_emit=rows(log,"CH14_PROFILE");all_received=rows(log,"CH14_RECEIPT")
    emitted=[e for e in all_emit if t0<=e["publish_end_ns"]<t1]
    callbacks=[e for e in all_received if t0<=e["wall_ns"]<t1]
    # Every source record must preserve original G03 guard, even outside window.
    assert all(0<=e["age_ms"]<=300 and 0<=e["oldest_age_ms"]<=300 for e in all_emit)
    assert len(emitted)>0 and all(gt_ok(e) for e in emitted)
    assert all(e["model_sha256"]==sha and e["generation"]==0 for e in emitted)
    assert all(abs(sum(e[k] for k in STAGES[:7])-e["pipeline_ms"])<1e-6 for e in emitted)
    assert len({e["stamp"] for e in emitted})==len(emitted)
    h=[x for x in observed["heartbeats"] if t0<=x["wall_ns"]<t1 and x["heartbeat_interval_ms"] is not None]
    assert h
    c=shutdown[0]["counters"];s=shutdown[0]["slot"];recon=count_reconcile(c,s)
    assert recon["accepted_residual"]==0 and recon["in_flight"]==0
    assert c["published"]==len(all_emit) and c["callbacks"]==len(all_received)
    # full-process reconciliation is independent of measurement-window boundary carry.
    assert recon["completed_not_published"]>=0
    inputs=[v for v in observed["inputs"] if t0<=v["wall_ns"]<t1]
    outputs=[v for v in observed["outputs"] if t0<=v["wall_ns"]<t1]
    emap={e["stamp"]:e for e in emitted};omap={e["stamp"]:e for e in outputs}
    overlap=set(emap)&set(omap)
    assert overlap and all(boxes_ok(emap[n]["boxes"],omap[n]["boxes"]) for n in overlap)
    stats={k:summarize([e[k] for e in emitted]) for k in STAGES}
    output_intervals=[(b["publish_end_ns"]-a_["publish_end_ns"])/1e6 for a_,b in zip(emitted,emitted[1:])]
    rr={}
    for k in ("detector","gazebo","bridge","tf"):
        rr[k]={}
        for field in ("cpu_pct","rss_mib"):
            vals=[v[k+"_"+field] for v in resources if v[k+"_"+field] is not None and v[k+"_pids"]]
            rr[k][field]=summarize(vals) if vals else None
    assert rr["detector"]["cpu_pct"] and rr["detector"]["rss_mib"] and rr["gazebo"]["cpu_pct"]
    hashes=Counter(e["image_sha256"] for e in emitted)
    result.update(status="PASS",source_outputs=len(emitted),source_callbacks=len(callbacks),observer_rgb=len(inputs),observer_detections=len(outputs),
                  observer_source_stamp_overlap=len(overlap),observer_only_stamps=len(set(omap)-set(emap)),source_only_stamps=len(set(emap)-set(omap)),
                  source_hz=len(emitted)/result["wall_seconds"],observed_input_hz=len(inputs)/result["wall_seconds"],observer_hz=len(outputs)/result["wall_seconds"],
                  dimensions=sorted(set((v["width"],v["height"]) for v in inputs)),nominal_sim_sensor_hz=10,rtf=observed["rtf"],
                  heartbeat=summarize([x["heartbeat_interval_ms"] for x in h]),heartbeat_misses=sum(x["heartbeat_interval_ms"]>200 for x in h),
                  output_intervals_ms=summarize(output_intervals) if output_intervals else None,
                  timing=stats,resources=rr,source_full_process=dict(counters=c,slot=s,reconciliation=recon),
                  source_image_hash_counts=dict(hashes),semantic_gt_misses=0,stale_emits=0,debug_counts=observed["debug_counts"],
                  worker_joined=True,device="CPU",precision="FP32",threads=2)
    write_csv(out/"metrics.csv",emitted);write_csv(out/"callbacks.csv",callbacks);save(out/"result.json",result)
    return result,emitted

def main():
    p=argparse.ArgumentParser();p.add_argument("--pt",type=Path,required=True);p.add_argument("--onnx",type=Path,required=True)
    p.add_argument("--sha256",required=True);p.add_argument("--assets",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--profiles",default="ABC");a=p.parse_args()
    assert digest(a.pt)==PT_SHA and digest(a.onnx)==a.sha256
    assert a.profiles and len(set(a.profiles))==len(a.profiles) and set(a.profiles)<=set(PROFILES)
    result=dict(status="PARTIAL",profiles={},D={"status":"N/A","reason":"optional TensorRT GPU not executed"},
                environment=dict(platform=platform.platform(),python=platform.python_version(),affinity=sorted(os.sched_getaffinity(0)),
                cpu_quota=Path("/sys/fs/cgroup/cpu.max").read_text().strip() if Path("/sys/fs/cgroup/cpu.max").exists() else None,
                class_map_sha256=CLASS_HASH,network_shape=[1,3,640,640],confidence=.5,iou=.45),comparisons={})
    ref={}
    try:
        for key in a.profiles:
            backend,mode=PROFILES[key];os.environ["ROS_DOMAIN_ID"]=str(80+ord(key)-ord("A"))
            row,emits=run_one(a,key,mode,backend);result["profiles"][key]=row
            ref[key]={}
            for e in emits:
                h=e["image_sha256"]
                if h in ref[key]:assert boxes_ok(ref[key][h],e["boxes"])
                else:ref[key][h]=e["boxes"]
            save(a.out/"comparison.json",result)
        for a_,b in ("AB","BC"):
            if a_ not in ref or b not in ref:continue
            overlap=set(ref[a_])&set(ref[b]);match=bool(overlap) and all(boxes_ok(ref[a_][h],ref[b][h]) for h in overlap)
            result["comparisons"][a_+b]=dict(shared_pixel_hashes=len(overlap),all_shared_boxes_equivalent=match,
                identical_pixel_sets=set(ref[a_])==set(ref[b]),model_latency_speedup=result["profiles"][a_]["timing"]["inference_ms"]["mean_ms"]/result["profiles"][b]["timing"]["inference_ms"]["mean_ms"])
            assert match,"no identical-image parity or detection mismatch"
        result["status"]="PASS" if set(a.profiles)==set("ABC") else "SCOPED_PASS"
    finally:save(a.out/"comparison.json",result)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for key,label in [("inference_ms","Model inference (ms)"),("age_ms","ROS source age (ms)"),("queue_ms","Worker queue (ms)")]:
        fig,ax=plt.subplots()
        ax.boxplot([[float(x[key]) for x in csv.DictReader((a.out/p/"metrics.csv").open())] for p in a.profiles],tick_labels=list(a.profiles))
        ax.set_ylabel(label);ax.set_xlabel("Profile");fig.tight_layout();fig.savefig(a.out/(key+".png"));plt.close(fig)
    fig,ax=plt.subplots();ax.bar(list(a.profiles),[result["profiles"][k]["source_hz"] for k in a.profiles]);ax.set_ylabel("Source outputs / wall second");fig.tight_layout();fig.savefig(a.out/"output_hz.png");plt.close(fig)
if __name__=="__main__":main()
