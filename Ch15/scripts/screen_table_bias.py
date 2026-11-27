import sys,json,math,zipfile,hashlib
from pathlib import Path
from table_approach_contract import entry_for,route
from arc_straight_profile import local,straight_command,wrap
from shapely.geometry import Polygon,box
from shapely.affinity import rotate,translate
FP=Polygon([(-.4634686765569823,-.2885523206836057),(.3944878597081477,-.2885523206836057),(.3944878597081477,.26606196787095665),(-.4634686765569823,.26606196787095665)])
def verified(path):
 z=zipfile.ZipFile(path);lines=z.read('sha256sums.txt').decode().splitlines();assert all(hashlib.sha256(z.read(n.lstrip('*').removeprefix('./'))).hexdigest()==h for h,n in (l.split(maxsplit=1) for l in lines));return z,len(lines)
def pose(x):
 q=x['qpos'];return (q[0],q[1],math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2)))
def proxy(z,r,shift):
 # Recorded local increments plus bounded command-delta yaw sensitivity;
 # unchanged physical stop increments; NOT a simulator.
 rows=[json.loads(l) for l in z.read('case/native/engine_observations.jsonl').splitlines()];p=r['phases'][-1];g=r['final_goal'];e=entry_for(g)
 start=p['release_sim_ns']/1e9;end=p['end_sim_ns']/1e9;settle=p['settle_sim_ns']/1e9
 points=[(x['sim_s'],pose(x)) for x in rows if start-1e-7<=x['sim_s']<=settle+1e-7];x,y,h=points[0][1]; y+=shift; d=0.; maxh=0.; rejected=False
 for (ta,a),(tb,b) in zip(points,points[1:]):
  dt=tb-ta; da=wrap(b[2]-a[2]); c0=straight_command(local(a,e)); c1=straight_command(local((x,y,h),e));
  if ta<end-1e-7:
   if c0 is None or c1 is None:rejected=True;break
   delta=c1[1]-c0[1];d+=min(1.,dt/.12)*(delta-d)
  else:d=0.
  # perturb recorded displacement direction, not magnitude
  dx=b[0]-a[0];dy=b[1]-a[1];dh=wrap(h-a[2]); x+=dx*math.cos(dh)-dy*math.sin(dh);y+=dx*math.sin(dh)+dy*math.cos(dh);h=wrap(h+da+1.08*d*dt);maxh=max(maxh,abs(h))
 return {'shift_m':shift,'xy_m':math.dist((x,y),g[:2]),'yaw_rad':abs(h-g[2]),'max_heading_rad':maxh,'rejected':rejected,'pose':(x,y,h)}
def main(world_archive,*archives):
 z,_=verified(world_archive);s=json.loads(z.read('case/native/scenario.json'));z.close();obs=[]
 for g in s['world_geometry']:
  if g['navigation_obstacle']:
   x,y,_=g['center'];hx,hy,_=g['half'];obs.append((g['name'],box(x-hx,y-hy,x+hx,y+hy)))
 for name,x,y,hx,hy in [('wall_left',-2,0,.05,2.5),('wall_right',4,0,.05,2.5),('wall_bottom',1,-2.5,3,.05),('wall_top',1,2.5,3,.05),('receiving_support',-.8,0,.045,.045),('target',3,1,.05,.05)]:obs.append((name,box(x-hx,y-hy,x+hx,y+hy)))
 results=[]
 for path in archives:
  z,n=verified(path);r=json.loads(z.read('case/native/segment_result.json'));g=r['final_goal'];start=r['phases'][1]['start_pose'];cs=[]
  for shift in [0,.015,.020,.025]:
   p=route(start,g,arc_bias_m=shift);d,name=min((translate(rotate(FP,h,origin=(0,0),use_radians=True),x,y).distance(o),name) for key in ('initial_turn','travel','arc','straight') for x,y,h in p[key] for name,o in obs);a={'shift_m':shift,'min_clearance_m':d,'nearest':name,'entry':p['entry']}
   if 'settled_pose' in r['phases'][-1]:a['proxy']=proxy(z,r,shift)
   cs.append(a)
  results.append({'archive':Path(path).name,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'verified_members':n,'arc_lateral_m':g[1]-r['phases'][2]['settled_pose'][1],'cases':cs});z.close()
 print(json.dumps({'scope':'static geometry and recorded increment sensitivity only; no actual candidate dynamics','cases':results},indent=2,allow_nan=False))
if __name__=='__main__':main(*sys.argv[1:])
