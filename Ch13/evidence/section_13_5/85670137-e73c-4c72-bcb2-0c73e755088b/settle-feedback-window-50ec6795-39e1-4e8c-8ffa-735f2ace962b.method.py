"""Read already-recorded captures; no synthetic force or runtime changes."""
import hashlib,json,math,uuid
from pathlib import Path
r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=b/'native-contact-component-gazebo-ab85a9a6-d9e2-404c-9ccc-a573f64122bb'
p=trial/'all_frames.json';frames=json.loads(p.read_bytes())['frames']
fault=json.loads((trial/'controller_report.json').read_bytes())['first_fault']
start=fault['phase_context']['_unload_start'];stop=fault['ros_ns'];rows=[];seen=set()
for f in frames:
 if not start<=f['ros_ns']<=stop:continue
 body=f['samples']['body'];stamp=body['stamp_ns']
 if stamp in seen:continue
 seen.add(stamp);data=body['data']
 linear=math.sqrt(sum(x*x for x in data['linear_velocity']));angular=math.sqrt(sum(x*x for x in data['angular_velocity']))
 rows.append({'decision_ros_ns':f['ros_ns'],'body_capture_ns':stamp,'linear_mps':linear,'angular_rps':angular,
  'passes_original_motion_settle':linear<=.003 and angular<=.01,
  'fl_calf_q':f['samples']['joints']['data']['position']['fl_calf_joint'],
  'fl_calf_qd':f['samples']['joints']['data']['velocity']['fl_calf_joint']})
segments=[]
for row in rows:
 flag=row['passes_original_motion_settle']
 if not segments or segments[-1]['passes']!=flag:segments.append({'passes':flag,'first_ros_ns':row['decision_ros_ns'],'last_ros_ns':row['decision_ros_ns'],'samples':0})
 segment=segments[-1];segment['last_ros_ns']=row['decision_ros_ns'];segment['samples']+=1
out={'scope':'observed_settle_gate_excludes_load_feedback_not_complete_runtime_trace',
 'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'unload_start_ros_ns':start,'failure_ros_ns':stop,
 'segments':segments,'rows':rows,'limits':{'linear_mps':.003,'angular_rps':.01},
 'caveat':'Gait also checks support and application credit. This proves motion eligibility absence, not every callback absence.'}
target=b/('settle-feedback-window-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'path':str(target),'segments':segments}))
