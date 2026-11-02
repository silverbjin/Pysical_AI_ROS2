"""Read-only /proc CPU by native OS thread for one owned runner identity."""
import hashlib,json,os,sys,time
from pathlib import Path
pid=int(sys.argv[1]);output=Path(sys.argv[2]);assert output.is_absolute() and not output.exists()
proc=Path('/proc')/str(pid)
def identity():
    stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
    assert proc.stat().st_uid==os.getuid(),'foreign UID'
    return dict(pid=pid,ppid=int(stat[1]),pgid=int(stat[2]),start_ticks=int(stat[19]),state=stat[0])
owner=identity();hz=os.sysconf('SC_CLK_TCK');start=time.monotonic();failure=None;count=0;ended=False
with output.open('x') as file:
    file.write(json.dumps(dict(kind='identity',owner=owner,uid=os.getuid(),clock_ticks=hz,helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),command=sys.argv))+'\n');file.flush()
    try:
        while time.monotonic()-start<2000.:
            try:current=identity()
            except FileNotFoundError:ended=True;break
            assert current['start_ticks']==owner['start_ticks'] and current['pgid']==owner['pgid'],'runner identity changed'
            if current['state'] in ('Z','X','x'):ended=True;break
            rows=[]
            for task in (proc/'task').iterdir():
                try:
                    text=(task/'stat').read_text();values=text.rsplit(')',1)[1].split()
                    rows.append(dict(tid=int(task.name),name=text.split('(',1)[1].rsplit(')',1)[0],state=values[0],user_ticks=int(values[11]),system_ticks=int(values[12]),start_ticks=int(values[19])))
                except FileNotFoundError:continue
            file.write(json.dumps(dict(kind='sample',wall_ns=time.monotonic_ns(),system_ns=time.time_ns(),threads=rows))+'\n');file.flush();count+=1;time.sleep(.25)
    except BaseException as error:failure=repr(error)
    file.write(json.dumps(dict(kind='closed',failure=failure,samples=count,observed_runner_exit=ended))+'\n')
if failure or not ended:raise SystemExit(1)