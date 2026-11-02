import hashlib,json,uuid
from pathlib import Path
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
mapping=root/'dart-static-mapping-7d150460-7eab-4ebd-a491-5dc92aa40dd4/evaluate.stdout'
native=root/'native-contact-component-gazebo-d50469aa-b0a0-402b-b8e5-f59f21ad31a0/native_controls.json'
records=json.loads(native.read_bytes())['records']
stamp=53130000000
frame=min(records,key=lambda r:abs(r['capture_ns']-stamp))
by_name={r['name']:r for r in frame['joints']}
d=json.loads(mapping.read_bytes())
for row in d['rows']:
 n=by_name[row['joint']]
 row.update({'native_capture_ns':frame['capture_ns'],'native_velocity':n['velocity'],
   'native_command_nm':n['force_command'],'native_transmitted_nm':n['projected_transmitted_effort'],
   'plus_Dv_predicted_command_nm':row['predicted_command_at_zero_velocity_nm']+row['damping']*n['velocity']})
 row['corrected_residual_nm']=row['plus_Dv_predicted_command_nm']-n['force_command']
 row['continuous_residual_nm']=row['continuous_static_nm']+row['damping']*n['velocity']-n['force_command']
d['caveats']=['Parent geometry at53.130s versus native state/force command at53.124s; not identical sample.',
 'Steady net acceleration assumed; full velocity bias and changing contact terms omitted.',
 'Massless optical frames explicitly zero; first DartLoader default-mass trial17.2101kg retained and not adopted.',
 'No runtime controller change, no whole robot test, no C1/G2 acceptance.']
d['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (mapping,native)}
d['max_abs_corrected_residual_nm']=max(abs(r['corrected_residual_nm']) for r in d['rows'])
d['max_abs_continuous_residual_nm']=max(abs(r['continuous_residual_nm']) for r in d['rows'])
p=root/('implicit-damping-comparison-'+str(uuid.uuid4())+'.json')
p.write_text(json.dumps(d,indent=2))
print(json.dumps({'path':str(p),'corrected_max':d['max_abs_corrected_residual_nm'],
 'continuous_max':d['max_abs_continuous_residual_nm'],'fl_calf':next(r for r in d['rows'] if r['joint']=='fl_calf_joint')},indent=2))
