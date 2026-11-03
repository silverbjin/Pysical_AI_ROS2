import hashlib,json,subprocess
from pathlib import Path
repo=Path('C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2');work=Path(__file__).resolve().parent;exe='C:/Program Files/Git/cmd/git.exe';base='Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
def git(*args):return subprocess.check_output([exe,'-c','gc.auto=0','-C',str(repo),*args])
current=git('rev-parse','HEAD').decode().strip();head='297423150010d49f28599cd8306ce3445b0d6049'
remote=git('ls-remote','origin','refs/heads/feat/ch13-section-13-5').decode().split()[0];assert remote==current
git('merge-base','--is-ancestor',head,current)
deleted=[p for p in git('diff','--diff-filter=D','--name-only','-z').decode().split('\0') if p]
rows=[]
for name in deleted:
 assert name.startswith(base+'/') and name.endswith(('.json','.jsonl'))
 path=Path(name);trial=path.parts[len(Path(base).parts)];relative=Path(*path.parts[len(Path(base).parts)+1:]).as_posix()
 record=json.loads((repo/base/trial/'retention.json').read_bytes());removed=next(r for r in record['removed'] if r['path']==relative)
 before=json.loads(git('show',head+':'+base+'/'+trial+'/retention.json'))
 assert before['result_sha256']==record['result_sha256'] and before['original_status']==record['original_status']
 digest=hashlib.sha256();size=0
 process=subprocess.Popen([exe,'-c','gc.auto=0','-C',str(repo),'show',head+':'+name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 while True:
  chunk=process.stdout.read(1024*1024)
  if not chunk:break
  digest.update(chunk);size+=len(chunk)
 assert process.wait()==0
 assert size==removed['size'] and digest.hexdigest()==removed['sha256'],name
 rows.append(dict(path=name,full_raw_commit=head,git_blob=git('rev-parse',head+':'+name).decode().strip(),bytes=size,sha256=digest.hexdigest(),retention_status=record['original_status'],full_replay_preserved_in_remote_history=True))
result=dict(scope='lossless Git preservation verification for automatic working-copy retirement; not acceptance',preserved_remote_commit=head,remote_sha_verified=True,paths=rows,total_bytes=sum(r['bytes'] for r in rows),working_copy_deletions_are_existing_retention=True,
 note='The original full raw bytes were committed/pushed and SHA-verified before the run. Each retired raw now matches that preserved Git blob; normal non-force descendants retain this history. Illustrative retained samples do not replace the full replay or change failure status.')
p=repo/base/'task8-retention-git-preservation-20261102.json';p.write_text(json.dumps(result,indent=2),encoding='utf-8');p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'verified_paths':len(rows),'preserved_bytes':result['total_bytes'],'remote_commit':head,'original_failures_unchanged':True},indent=2))
