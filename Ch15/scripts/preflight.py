#!/usr/bin/env python3
"""Read-only scoped preflight. No installs, downloads or actuator launch."""
import argparse, hashlib, json, pathlib, platform, re, shutil, subprocess, sys
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
def check(root,pin,profile,assets,ack):
    lock=json.loads((root/"Ch15/dependencies/reuse.audit.json").read_text())
    actual=git(root,"rev-parse","HEAD")
    if not re.fullmatch("[0-9a-f]{40}",pin) or actual!=pin:
        raise ValueError("SOURCE_SHA_DRIFT")
    for path,expected in lock["protected_trees"].items():
        if git(root,"rev-parse",f"HEAD:{path}")!=expected:
            raise ValueError("PROTECTED_TREE_DRIFT:"+path)
    if profile=="physical_basic":
        if not ack or assets is None:
            raise ValueError("ASSET_ACCESS_OR_RIGHTS_UNCONFIRMED")
        for row in lock["ch13"]["assets"]:
            p=assets/row["path"]
            if not p.is_file() or p.stat().st_size!=row["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest()!=row["sha256"]:
                raise ValueError("ASSET_MISSING_OR_DRIFT:"+row["path"])
    osinfo=pathlib.Path("/etc/os-release").read_text()
    if 'ID=ubuntu' not in osinfo or 'VERSION_ID="24.04"' not in osinfo or sys.version_info[:2]!=(3,12) or platform.machine()!="x86_64":
        raise ValueError("TARGET_OS_ABI")
    if not pathlib.Path("/opt/ros/jazzy/setup.bash").is_file():
        raise ValueError("ROS_JAZZY_MISSING")
    for cmd in ["ros2","colcon"]:
        if not shutil.which(cmd): raise ValueError("MISSING_TOOL:"+cmd)
    import rclpy
    import rosbag2_py
    if "mcap" not in rosbag2_py.get_registered_writers():
        raise ValueError("MCAP_MISSING")
    if profile=="cube" and not shutil.which("gz"):
        raise ValueError("GAZEBO_MISSING")
    return {"source_sha":actual,"profile":profile,"result":"SCOPED_PREFLIGHT_PASS","python":sys.version,"platform":platform.platform(),"physical_runtime_verified":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=pathlib.Path,required=True);p.add_argument("--pin",required=True)
    p.add_argument("--profile",choices=["mock","cube","physical_basic"],required=True)
    p.add_argument("--assets",type=pathlib.Path);p.add_argument("--acknowledge-assets",action="store_true")
    p.add_argument("--receipt",type=pathlib.Path,required=True)
    args=p.parse_args()
    try:
        row=check(args.repo,args.pin,args.profile,args.assets,args.acknowledge_assets);code=0
    except Exception as exc:
        row={"result":"BLOCKED","reason":str(exc),"profile":args.profile,"requested_sha":args.pin};code=2
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(row,indent=2)+"\n")
    print(json.dumps(row));return code
if __name__=="__main__":sys.exit(main())
