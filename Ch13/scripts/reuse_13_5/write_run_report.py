"""Generate a small Markdown report from actual replay outputs, including failures."""
import json,sys
from pathlib import Path
out=Path(sys.argv[1])
def read(name):
 p=out/name
 return json.loads(p.read_text()) if p.exists() else {}
s=read('navigation_summary.json');v=read('navigation_verification.json');e=read('engine.json');residual=read('residual_processes.json')
rows=[f'# {out.name} 실행 보고서', '',f"- 시나리오: `{s.get('case','unknown')}`",f"- 실제 실행: `{s.get('result','INCOMPLETE')}` / 독립 검증: `{v.get('result','NOT_RUN')}`",f"- terminal: `{s.get('terminal_status')}` / cancel ACK: `{s.get('cancel_ack')}`",f"- 실제 목표 오차: `{s.get('actual_goal_error_m')}` m / `{s.get('actual_goal_yaw_error_rad')}` rad",f"- terminal 뒤 정착: `{s.get('terminal_to_settled_wall_s')}` wall s",f"- 엔진: `{e.get('sim_s')}` sim s / `{e.get('wall_s')}` wall s / force-cap ratio `{e.get('max_force_cap_ratio')}`",f"- 정상 종료: `{e.get('normal_shutdown_requested')}` / RX join: `{e.get('rx_joined')}` / upstream join: `{e.get('upstream_threads_joined')}`",f"- 자식 정상 회수: `{s.get('clean_launch_exits')}/{len(s.get('owned_launch_pids',[]))}` / 잔여: `{s.get('remaining_launch_pids')}` / 후검사: `{residual.get('result','NOT_RUN')}`",'', '검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.']
if s.get('error'):rows+=['','## 최초 실행 오류','', '```text',s['error'],'```']
(out/'RUN_REPORT_KO.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
