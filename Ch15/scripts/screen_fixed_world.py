"""Verified archived geometry only; no dynamics, visibility or ROS claim."""
import hashlib,json,sys,zipfile
from pathlib import Path
from shapely.geometry import Polygon,box
from shapely.affinity import rotate,translate
from table_approach_contract import route
FP=Polygon([(-.4634686765569823,-.2885523206836057),(.3944878597081477,-.2885523206836057),(.3944878597081477,.26606196787095665),(-.4634686765569823,.26606196787095665)])
REQUIRED=.12726434651956073

def verified(path):
    z=zipfile.ZipFile(path);lines=z.read('sha256sums.txt').decode().splitlines()
    for line in lines:
        h,n=line.split(maxsplit=1);assert hashlib.sha256(z.read(n.lstrip('*').removeprefix('./'))).hexdigest()==h
    return z,len(lines)

def main(world,*archives):
    z,_=verified(world)
    with z:s=json.loads(z.read('case/native/scenario.json'))
    obstacles=[]
    for g in s['world_geometry']:
        if g['navigation_obstacle']:
            x,y,_=g['center'];hx,hy,_=g['half'];obstacles.append((g['name'],box(x-hx,y-hy,x+hx,y+hy)))
    for name,x,y,hx,hy in [('wall_left',-2,0,.05,2.5),('wall_right',4,0,.05,2.5),('wall_bottom',1,-2.5,3,.05),('wall_top',1,2.5,3,.05),('receiving_support',-.8,0,.045,.045)]:obstacles.append((name,box(x-hx,y-hy,x+hx,y+hy)))
    cases=[]
    for p in archives:
        z,n=verified(p)
        with z:r=json.loads(z.read('case/native/segment_result.json'))
        start=r['phases'][1]['start_pose'];g=r['initial_goal'];path=route(start,g);scores={}
        for key in ('initial_turn','travel','arc','straight'):
            ds=[(translate(rotate(FP,h,origin=(0,0),use_radians=True),x,y).distance(o),name) for x,y,h in path[key] for name,o in obstacles]
            d,ob=min(ds);scores[key]=dict(minimum_clearance_m=d,nearest=ob,samples=len(path[key]));assert d>=REQUIRED,(key,d)
        cases.append(dict(archive=Path(p).name,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest(),verified_members=n,start=start,goal=g,entry=path['entry'],phases=scores))
    print(json.dumps(dict(result='PASS_ARCHIVED_FIXED_WORLD_SCREEN',scope='2D geometry only; actual table approach NOT_RUN',required_m=REQUIRED,cases=cases),indent=2))
if __name__=='__main__':main(*sys.argv[1:])
