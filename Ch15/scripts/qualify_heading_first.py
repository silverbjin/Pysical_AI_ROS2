#!/usr/bin/env python3
"""Offline 2-D candidate admission only, using verified native archives."""
import argparse, hashlib, json, math, zipfile
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.affinity import rotate, translate

# Ch13 nav2_params.yaml and scene.py at immutable source 1931cac9.
FOOTPRINT = Polygon([(-.4634686765569823,-.2885523206836057),(.3944878597081477,-.2885523206836057),(.3944878597081477,.26606196787095665),(-.4634686765569823,.26606196787095665)])
PADDING = .01
DRIFT_ALLOWANCE = .11  # empirical screening allowance; NOT a proven dynamic bound
STEP_M, STEP_RAD = .005, math.radians(1)
RADIUS = max(math.hypot(x,y) for x,y in FOOTPRINT.exterior.coords)
INTERPOLATION = STEP_M/2 + RADIUS*STEP_RAD/2
REQUIRED = PADDING + DRIFT_ALLOWANCE + INTERPOLATION

def segment(p,q):
    d=math.dist(p[:2],q[:2]); a=math.atan2(math.sin(q[2]-p[2]),math.cos(q[2]-p[2]))
    n=max(1, math.ceil(d/STEP_M), math.ceil(abs(a)/STEP_RAD))
    for i in range(n+1):
        yield (p[0]+(q[0]-p[0])*i/n,p[1]+(q[1]-p[1])*i/n,p[2]+a*i/n)

def read_case(path):
    with zipfile.ZipFile(path) as z:
        manifest=z.read('sha256sums.txt').decode().splitlines()
        for line in manifest:
            h,n=line.split(maxsplit=1); assert hashlib.sha256(z.read(n.lstrip('*').removeprefix('./'))).hexdigest()==h
        def read(n): return json.loads(z.read('case/native/'+n+'.json'))
        s,nav,bt=read('scenario'),read('navigation_summary'),read('bt_summary')
        assert s['name']=='level2_obstacles' and s['approach_bearings']==[0.0]
        event=next(e for e in bt['port']['events'] if e['event']=='survey_terminal_and_settled')
        rows=[json.loads(l) for l in z.read('case/native/engine_observations.jsonl').splitlines()]
        row=min(rows,key=lambda r:abs(r['sim_s']-event['clock_ns']/1e9))
        assert abs(row['sim_s']-event['clock_ns']/1e9)<=.02
        x,y,_,w,a,b,c=row['qpos'][:7]
        start=(x,y,math.atan2(2*(w*c+a*b),1-2*(b*b+c*c)))
        obs=[]
        for g in s['world_geometry']:
            if g['navigation_obstacle']:
                gx,gy,_=g['center']; hx,hy,_=g['half']; obs.append((g['name'],box(gx-hx,gy-hy,gx+hx,gy+hy)))
        for name,gx,gy,hx,hy in [('wall_left',-2,0,.05,2.5),('wall_right',4,0,.05,2.5),('wall_bottom',1,-2.5,3,.05),('wall_top',1,2.5,3,.05),('receiving_support',-.8,0,.045,.045)]:
            obs.append((name,box(gx-hx,gy-hy,gx+hx,gy+hy)))
        return start,tuple(nav['target']),obs,len(manifest)

def qualify(start,target,obs,offset):
    tx,ty,th=target; sx=tx-offset*math.cos(th); sy=ty-offset*math.sin(th)
    b=math.atan2(sy-start[1],sx-start[0])
    poses=[start,(*start[:2],b),(sx,sy,b),(sx,sy,th),target]
    phases=[]
    for name,p,q in zip(('initial_turn','travel','heading_alignment','final_straight'),poses,poses[1:]):
        min_d=float('inf'); near=None; samples=0
        for x,y,yaw in segment(p,q):
            g=translate(rotate(FOOTPRINT,yaw,origin=(0,0),use_radians=True),x,y)
            d,ob=min((g.distance(o),n) for n,o in obs)
            if d<min_d: min_d,near=d,ob
            samples+=1
        phases.append(dict(phase=name,samples=samples,minimum_clearance_m=min_d,nearest_obstacle=near,pass_screen=min_d>=REQUIRED))
    return dict(offset_m=offset,poses=poses,phases=phases,pass_screen=all(p['pass_screen'] for p in phases))

def main():
    p=argparse.ArgumentParser(); p.add_argument('archives',nargs='+',type=Path); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    results=[]
    for f in a.archives:
        start,target,obs,n=read_case(f)
        positive=qualify(start,target,obs,.40); rejected=qualify(start,target,obs,.45)
        assert positive['pass_screen'],positive
        assert not rejected['pass_screen'],rejected
        results.append(dict(archive_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),verified_members=n,positive=positive,rejected_control=rejected))
    report=dict(scope='2D navigation footprint screening only; no dynamics, actual Nav2 trajectory, 3D collision, visibility or L2 acceptance',required_clearance_m=REQUIRED,padding_m=PADDING,empirical_drift_allowance_m=DRIFT_ALLOWANCE,interpolation_allowance_m=INTERPOLATION,cases=results,result='OFFLINE_GEOMETRY_SCREEN_PASS')
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__':main()
