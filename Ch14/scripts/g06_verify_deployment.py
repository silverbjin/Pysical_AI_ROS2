"""Check actual Docker inspect + source traces + independent DDS evidence."""
import argparse,json,re,os
from pathlib import Path
def load(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);p.add_argument("--image-id",required=True);p.add_argument("--phase",choices=["single","compose"],required=True);a=p.parse_args()
    out=a.out;phase=a.phase
    if phase=="single":
        inspectors=[load(out/"single-inspect.json")[0],load(out/"monitor-inspect.json")[0],load(out/"sensor-inspect.json")[0]]
        text=(out/"single-detector.log").read_text()
    else:
        inspectors=load(out/"compose-inspect.json");text=(out/"compose-ai.log").read_text()
    assert len(inspectors)==3
    for d in inspectors:
        assert d["Image"]==a.image_id and d["State"]["ExitCode"]==0 and not d["State"]["OOMKilled"] and not d["State"]["Running"]
        assert d["Config"]["User"]==f"{os.getuid()}:{os.getgid()}" and os.getuid()!=0
        hc=d["HostConfig"];assert "ALL" in hc.get("CapDrop",[]) and not hc["Privileged"] and hc["PidMode"]!="host" and not hc.get("Devices") and hc["NetworkMode"]=="host"
        for m in d["Mounts"]:
            assert m["Destination"] in ("/models","/bags","/evidence")
            if m["Destination"] in ("/models","/bags"):assert not m["RW"]
    profile=[json.loads(x.split("CH14_PROFILE ",1)[1]) for x in text.splitlines() if "CH14_PROFILE " in x]
    shutdown=[json.loads(x.split("CH14_SHUTDOWN ",1)[1]) for x in text.splitlines() if "CH14_SHUTDOWN " in x]
    assert len(shutdown)==1 and shutdown[0]["worker_joined"] and not shutdown[0]["slot"].get("worker_alive",False)
    assert profile and len(profile)==shutdown[0]["counters"]["published"]
    assert all(0<=x["oldest_age_ms"]<=300 for x in profile)
    assert all(x["generation"]==0 for x in profile)
    obs=load(out/"monitor.json");assert obs["status"]=="PASS" and obs["matched_points"]>=3 and obs["clock_publishers"]==[1]
    em={x["stamp"] for x in profile};ob={x["stamp"] for x in obs["outputs"]}
    assert len(em&ob)>=3
    result=dict(status="PASS",scope=phase,image_id=a.image_id,container_ids=[x["Id"] for x in inspectors],exit_codes=[x["State"]["ExitCode"] for x in inspectors],
                source_emits=len(profile),source_max_age_ms=max(x["oldest_age_ms"] for x in profile),observed=len(ob),source_observer_overlap=len(em&ob),
                semantic_stamps=obs["semantic_stamps"],matched_points=obs["matched_points"],clock_publishers=obs["clock_publishers"],debug_counts=obs["debug_counts"],worker_joined=True,
                independent_receive_age_minmax_ms=[min(x["observed_age_ms"] for x in obs["independent_receive_age"]),max(x["observed_age_ms"] for x in obs["independent_receive_age"])] if obs["independent_receive_age"] else None)
    (out/"verified.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
if __name__=="__main__":main()
