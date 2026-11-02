"""Independent matrix closure; does not convert a failed scenario to PASS."""
from pathlib import Path
import hashlib,json,sys
from run_acceptance import frozen
root=Path(__file__).resolve().parents[3];fpath=Path(sys.argv[1]);f=json.loads(fpath.read_text());out=Path(sys.argv[2]);m=json.loads((out/'matrix.json').read_text());frozen(f)
checks={'freeze_sha256':hashlib.sha256(fpath.read_bytes()).hexdigest()==m['freeze_sha256'],'scenario_set':[x['case'] for x in m['cases']]==f['scenarios'],'runner_pass':m['result']=='PASS'};rows=[]
for c in m['cases']:
 p=root/'Ch13/evidence/section_13_5_reuse'/c['uuid'];s=json.loads((p/'navigation_summary.json').read_text());v=json.loads((p/'navigation_verification.json').read_text()) if (p/'navigation_verification.json').exists() else {};r=json.loads((p/'residual_processes.json').read_text());checks[c['case']]=s['result']=='PASS' and v.get('result')=='PASS' and r['result']=='PASS' and c['exit_code']==0
 expected=6 if c['case']=='blocked' else (5 if c['case'] in ['cancel','raw_loss'] else 4);checks[c['case']+'_terminal']=s.get('terminal_status')==expected
 if c['case']=='raw_loss':checks['raw_restored_stays_fault']=s.get('no_auto_resume_after_raw_return') is True and s['raw_expiry_decision_latency_s']<=f['raw_expiry_zero_wall_s']
 if c['case']=='obstacle':checks['actual_obstacle_bypass']=s.get('max_abs_y_m',0)>.45
 if c['case']=='vision':checks['selected_vision_rate']=json.loads((p/'vision_summary.json').read_text())['inference_cap_wall_hz']==f['vision_inference_wall_hz']
 rows.append(f"| {c['case']} | [{c['uuid'][:8]}](../evidence/section_13_5_reuse/{c['uuid']}/RUN_REPORT_KO.md) | {s['result']}/{v.get('result','NOT_RUN')} | {s.get('terminal_status')} | {s.get('actual_goal_error_m')} | {s.get('terminal_to_settled_wall_s')} |")
result={'result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'freeze_sha256':m['freeze_sha256']};(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
text=['# R5 동결 인수 보고서','',f"**결과: {result['result']}**. 이 표는 실제 실행 JSON에서 자동 생성했다. FAIL/미실행을 성공으로 간주하지 않는다.",'',f"고정본: `{fpath.name}`, SHA256 `{m['freeze_sha256']}`. 필수 각1회;3회 반복은 미실시 확장이다.",'','| 시나리오 | 증거 | 실행/독립검증 | terminal | 실제 위치 오차 m | 정착 wall s |','|---|---|---|---|---|---|']+rows+['','세부 고장·정착 metrics·실제 RGB-D hash/과거TF·정상 회수는 각 실행 보고서와 JSON을 따른다. 도달 불가는 비어 있는 목표와 통로 차단을 사용한다. raw 손실은 소유 경계 PID를 일시 정지했다 복귀시켜 만료와 자동 재개 금지를 확인한다.','','## 검증 범위','','MuJoCo, 고정 장애물, engine ground-truth localization, 붉은 고정 작업물의 실제 RGB-D 표면 관측과 위치 IK다. 충돌 형상 기반 카메라 화면이며 일반 인식·AMCL/SLAM·Gazebo·실기·MoveIt/파지·동적 물체 추적은 검증하지 않았다. 기본10Hz와 선택15Hz를 구분하며 이 고정본의 비전 인수는15Hz다.','','원본13.3/13.4의 별도 회귀, 신규 isolated 설치 감사, 출처·환경 및 게시 SHA는 최종 종합 보고서에서 따로 기록한다.']
(root/'Ch13/docs/SECTION_13_5_REUSE_R5_REPORT_KO.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));sys.exit(0 if result['result']=='PASS' else 1)
