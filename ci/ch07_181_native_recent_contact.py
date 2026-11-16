"""Issue #181: independent recent Gazebo native physical finger/rod contact.

ROS /joint_states and Action SUCCEEDED are insufficient. Read-only sensor data
are used to require real bilateral contact with positive force immediately
before actual release. Never create contacts or relax FJT tolerance.
"""
import math,re
from pathlib import Path
FINGER=("finger1","finger2")
PAIR={
  "finger1":"my_robot::finger1::finger1_collision",
  "finger2":"my_robot::finger2::finger2_collision"}
ROD="g04_grasp_cylinder::cylinder_link::cylinder_collision"
MAX_AGE_SIM_SECONDS=.4
MIN_FORCE_N=.05
STAMP_RE=re.compile(r"stamp\s*\{\s*sec:\s*(\d+)\s+nsec:\s*(\d+)")
NAME_RE=re.compile(r'name:\s*"([^"]+)"')
FORCE_RE=re.compile(r'body_1_wrench\s*\{\s*force\s*\{\s*x:\s*([-+\deE.]+)\s*y:\s*([-+\deE.]+)\s*z:\s*([-+\deE.]+)')

def contact_tail(path,max_tail=150000):
    path=Path(path)
    if not path.is_file():return ""
    with path.open("rb") as f:
        f.seek(0,2);size=f.tell()
        f.seek(max(size-max_tail,0))
        return f.read().decode(errors="replace")

def recent_native_finger_rod_contact(path,finger,now_sim_s):
    if finger not in FINGER or not math.isfinite(float(now_sim_s)):
        raise ValueError("G04B_NATIVE_CONTACT_FINGER_OR_TIME_INVALID")
    text=contact_tail(path)
    fresh=[]
    for block in text.split("\ncontact {\n")[1:]:
        stamp=STAMP_RE.search(block)
        names=NAME_RE.findall(block[:480])
        if stamp is None or ROD not in names or PAIR[finger] not in names:continue
        t=int(stamp.group(1))+int(stamp.group(2))*1e-9
        age=now_sim_s-t
        if age<0 or age>MAX_AGE_SIM_SECONDS:continue
        m=FORCE_RE.search(block)
        if m is None:continue
        v=[float(x) for x in m.groups()]
        if not all(math.isfinite(x) for x in v):continue
        force=math.sqrt(sum(x*x for x in v))
        if force>MIN_FORCE_N:fresh.append((t,force))
    return {"finger":finger,"recent_contact_events":len(fresh),
            "max_force_N":max((x[1] for x in fresh),default=0),
            "last_contact_sim_s":max((x[0] for x in fresh),default=None),
            "native_positive_force_fresh":len(fresh)>=3}

def require_bilateral_pre_release_contact(dir_path,now_sim_s):
    d=Path(dir_path)
    readings={name:recent_native_finger_rod_contact(
        d/("diag_"+name+"_contacts.log"),name,now_sim_s) for name in FINGER}
    return {"per_finger":readings,
            "both_native_fresh_positive_force":all(
                p["native_positive_force_fresh"] for p in readings.values()),
            "sim_time_s":now_sim_s}

# Cycle17: original Gazebo Sim8 same-PostUpdate native wrench, no contact
# synthesis and no acceptance-threshold relaxation. The ContactSensorData
# embedded contact stamp may be zero: use the real ECS UpdateInfo.simTime.
import csv
ECS_FORCE_COLUMNS=("sim_time_s",
  "f1_collision_present","f1_contact_ecs_present","f1_rod_pair_count",
  "f1_max_rod_contact_force_N",
  "f2_collision_present","f2_contact_ecs_present","f2_rod_pair_count",
  "f2_max_rod_contact_force_N")

def require_bilateral_same_ecs_frame_force(path,now_sim_s):
    if not isinstance(now_sim_s,(int,float)) or not math.isfinite(now_sim_s) or now_sim_s<0:
        raise ValueError("C17_INVALID_SIM_TIME")
    path=Path(path)
    fresh={name:[] for name in FINGER}
    result={"per_finger":{},"both_native_fresh_positive_force":False,
            "sim_time_s":float(now_sim_s),
            "source":"GAZEBO_SIM8_READONLY_SAME_POSTUPDATE_ECS_CONTACT_WRENCH",
            "evidence_path":str(path)}
    if not path.is_file():
        result["reason"]="C17_NATIVE_SAME_ECS_CSV_MISSING"
    else:
        with path.open("rb") as file:
            first=file.readline().decode(errors="replace").strip()
            names=first.split(",")
            if not set(ECS_FORCE_COLUMNS).issubset(set(names)):
                result["reason"]="C17_NATIVE_SAME_ECS_FORCE_SCHEMA_MISSING"
            else:
                head_end=file.tell()
                file.seek(0,2);size=file.tell()
                start=max(head_end,size-196608)
                file.seek(start);raw=file.read()
                lines=raw.decode(errors="replace").splitlines()
                if start>head_end and lines:lines=lines[1:]
                if not raw.endswith(b"\n") and lines:lines=lines[:-1]
                reader=csv.DictReader([first]+lines)
                for row in reader:
                    try:
                        t=float(row["sim_time_s"])
                    except (TypeError,ValueError):
                        continue
                    if not math.isfinite(t) or not 0<=now_sim_s-t<=MAX_AGE_SIM_SECONDS:
                        continue
                    for short,name in (("f1","finger1"),("f2","finger2")):
                        try:
                            cp=int(row[short+"_collision_present"])
                            dp=int(row[short+"_contact_ecs_present"])
                            count=int(row[short+"_rod_pair_count"])
                            force=float(row[short+"_max_rod_contact_force_N"])
                        except (TypeError,ValueError,KeyError):
                            continue
                        if cp!=1 or dp!=1 or count<1 or not math.isfinite(force):
                            continue
                        if force>MIN_FORCE_N:fresh[name].append((t,force))
    for name in FINGER:
        v=fresh[name]
        result["per_finger"][name]={
            "finger":name,"recent_contact_events":len(v),
            "max_force_N":max((x[1] for x in v),default=0.),
            "last_contact_sim_s":max((x[0] for x in v),default=None),
            "native_positive_force_fresh":len(v)>=3}
    result["both_native_fresh_positive_force"]=all(
        result["per_finger"][n]["native_positive_force_fresh"] for n in FINGER)
    return result
