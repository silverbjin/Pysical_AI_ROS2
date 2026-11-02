"""Stream original operational frames; retain every failure count and first raw witness."""
import json,sys,time,uuid
from pathlib import Path
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'Ch13/scripts'))
from integrated_robot_navigation.samples import Sample,sample_valid
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
original=root/'native-g2-mujoco-e5f0aea4-bbea-427d-8d25-f020bfbe78fd'
target=root/('interrupted-freshness-'+str(uuid.uuid4()));target.mkdir()
print('FRESHNESS',target,flush=True)
checks={};frames=0;stages={'stand','calibrate','forward','left','right','reverse','stopped'}
with (original/'observations.jsonl').open('rb') as source:
    for line in source:
        if not line.startswith(b'{"kind": "frame",'):continue
        row=json.loads(line)['value']
        if row['stage'] not in stages:continue
        frames+=1
        for key in ('joints','imu','contacts','body','scan','native_com'):
            sample=Sample(**row['samples'][key]);limit=300_000_000 if key=='scan' else 200_000_000
            ok,reason=sample_valid(sample,row['ros_ns'],row['wall_ns'],0,max_age_ns=limit)
            info=checks.setdefault(key,dict(failures=0,max_ros_age_ms=-1e99,max_wall_age_ms=-1e99,examples=[]))
            ros_age=(row['ros_ns']-sample.stamp_ns)/1e6;wall_age=(row['wall_ns']-sample.received_ns)/1e6
            info['max_ros_age_ms']=max(info['max_ros_age_ms'],ros_age)
            info['max_wall_age_ms']=max(info['max_wall_age_ms'],wall_age)
            if ok:continue
            info['failures']+=1
            detail=dict(reason=reason,stage=row['stage'],ros_ns=row['ros_ns'],wall_ns=row['wall_ns'],
                capture_ns=sample.stamp_ns,first_receipt_ns=sample.received_ns,ros_age_ms=ros_age,
                wall_age_ms=wall_age,crawl=row.get('crawl'))
            if len(info['examples'])<4:info['examples'].append(detail)
            info['last_failure']=detail
            if not (target/'first_failed_frame.json').exists():
                (target/'first_failed_frame.json').write_text(json.dumps(row,indent=2))
report=dict(scope='all_operational_original_frames_no_exclusion_no_promotion',original=str(original),frames=frames,sensors=checks)
(target/'freshness.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
