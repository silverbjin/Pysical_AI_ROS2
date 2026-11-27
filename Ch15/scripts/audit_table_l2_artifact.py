#!/usr/bin/env python3
"""Independently audit a published table L2 receipt (not withheld MCAP bytes)."""
import argparse,hashlib,json,zipfile
from pathlib import Path
import yaml
from table_l2_contract import TOPICS,bag_checks,goal_trace_matches
from table_engine_audit import audit_phases


def audit(path,expected_sha=None):
    with Path(path).open('rb') as f:archive_sha=hashlib.file_digest(f,'sha256').hexdigest()
    if expected_sha and archive_sha!=expected_sha:raise ValueError('ZIP SHA mismatch')
    with zipfile.ZipFile(path) as z:
        verified=set()
        for line in z.read('sha256sums.txt').decode().splitlines():
            h,name=line.split(maxsplit=1);name=name.lstrip('*').removeprefix('./')
            if name in verified or hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('member mismatch '+name)
            verified.add(name)
        if set(z.namelist())!=verified|{'sha256sums.txt'} or len(z.namelist())!=len(set(z.namelist())):raise ValueError('unexpected archive member')
        def j(name):return json.loads(z.read('case/native/'+name+'.json'))
        def rows(name):return [json.loads(l) for l in z.read('case/native/'+name+'.jsonl').splitlines()]
        base=dict(archive_sha256=archive_sha,verified_members=len(verified),scope='independent receipt and engine audit; MCAP raw bytes intentionally withheld')
        if 'case/native/basic_result.json' not in verified:return {**base,'result':'NOT_RUN','reason':'no actual basic result'}
        grade=j('basic_result');s=j('segment_result');e=j('engine');bt=j('bt_summary');m=j('mcap_audit');nav=j('navigation_summary');telemetry=j('telemetry_delivery')
        independent=audit_phases(rows('engine_observations'),s['phases'],s['entry_goal'],s['final_goal'],e)
        meta_bytes=z.read('case/native/bag/metadata.yaml')
        meta=yaml.safe_load(meta_bytes)['rosbag2_bagfile_information']
        payload=json.loads(z.read('bag-payload-receipt.json'))
        meta_counts={v['topic_metadata']['name']:v['message_count'] for v in meta['topics_with_message_count']}
        payload_mcap=sorted([x for x in payload if x['name'].endswith('.mcap')],key=lambda x:x['name'])
        reported_mcap=sorted(m.get('mcap_files',[]),key=lambda x:x['name'])
        ticks=rows('bt_ticks');last=ticks[-1] if ticks else {};nodes=last.get('nodes',{})
        physics=e.get('pick_physics',{}).get('rows',[]);base_x=[v['base_xyz'][0] for v in physics]
        g=j('gc_policy_receipt');ack=s.get('shutdown_ack');first=s.get('startup_traces',{}).get('gateway',{}).get('first_fault')
        nav_fault=s.get('startup_traces',{}).get('navigation',{}).get('first_fault')
        metadata_receipt=[x for x in payload if x['name']=='metadata.yaml']
        checks=dict(original_assessor=grade.get('original_basic_assessor_result')=='PASS' and len(grade.get('checks',{}))==10 and all(v is True for v in grade['checks'].values()),
            segment=s.get('result')=='PASS_SCOPED_TABLE_SEGMENT' and all(v is True for v in s['checks'].values()),
            independent_engine=independent['result']=='PASS',
            exact_goals=goal_trace_matches(bt['goals'],s['phases']),
            terminal=bt.get('terminal')=='SUCCESS' and bt.get('worker_joined') is True and bt['port'].get('exit_code')==0 and bt['port'].get('closed') is True and not bt['port'].get('error'),
            steps=bt['port'].get('requested')==['navigate','find','finish'] and set(bt['port']['completed'])=={'navigate','find','finish'},
            terminal_tick=last.get('terminal')=='SUCCESS' and last.get('root')=='SUCCESS' and all(nodes.get(k)=='SUCCESS' for k in ('navigate','find','finish')),
            world=bool(base_x and min(base_x)<.45 and max(base_x)>.95 and max(v['ramp_contact_N'] for v in physics)>1. and 'find' in bt['port']['completed']),
            gc_policy=g.get('restored') is True and g.get('collections',[None,None,None])[2]==0 and 0<g.get('peak_rss_kib',0)<=4194304,
            shutdown_trace=bool(ack and not nav_fault and (not first or (first['reason']=='INPUT_OR_CLOCK_TIMEOUT' and first['decision_wall']>=ack['wall'] and first['clock_ns']>=ack['clock_ns']))),
            session=bool(bt.get('session') and bt['session']==s['mission_session']==e['manipulation']['last_status']['session'] and all(v.get('session')==bt['session'] for v in bt['port']['completed'].values())),
            no_manipulation=e.get('arm_events')==[] and e['manipulation']['arm_events']==[] and e['manipulation']['gripper_force_events']==[],
            bag_content_ci=m.get('result')=='PASS' and all(v is True for v in m['checks'].values()),
            bag_metadata=meta['storage_identifier']=='mcap' and set(meta_counts)==set(TOPICS) and meta_counts==m.get('counts') and all(x>0 for x in meta_counts.values()) and sum(meta_counts.values())==meta['message_count'],
            bag_payload_receipt=bool(payload_mcap and payload_mcap==reported_mcap and sorted(x['name'] for x in payload_mcap)==sorted(meta['relative_file_paths']) and all(x['bytes']>0 and len(x['sha256'])==64 for x in payload_mcap)),
            metadata_payload_receipt=metadata_receipt==[dict(name='metadata.yaml',bytes=len(meta_bytes),sha256=hashlib.sha256(meta_bytes).hexdigest())],
            bag_sequence=bool(len(m.get('start_stamps',[]))==1 and m.get('first_motion') is not None and m['start_stamps'][0]<=m['first_motion']<=m['last_motion'] and bool(m.get('terminal_stamps')) and m['last_motion']<=max(m['terminal_stamps'])),
            bag_closed=grade.get('bag_closed') is True,
            clean_children=nav.get('launch_exit_code')==0 and nav.get('remaining_launch_pids')==[] and len(nav.get('owned_launch_pids',[]))==nav.get('clean_launch_exits')==11,
            telemetry=telemetry.get('joined') is True and telemetry.get('write_errors')==0,
            residual=json.loads(z.read('case/after.json')).get('result')=='PASS',
            scope=grade.get('original_native_l2_pass') is False and grade.get('full_mission_success') is False)
        return {**base,'result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'independent':independent,'mcap_counts':meta_counts,'mcap_payload_receipt':reported_mcap}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip');p.add_argument('--sha256');a=p.parse_args();r=audit(a.zip,a.sha256);print(json.dumps(r,indent=2,allow_nan=False));raise SystemExit(0 if r['result']=='PASS' else 1)
