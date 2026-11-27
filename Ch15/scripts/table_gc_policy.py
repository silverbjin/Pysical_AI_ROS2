"""Ch15-only bounded Python 3.12 GC policy; never modifies Ch13 or native guards."""
import gc,json,resource,sys,time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def defer_full_collection(receipt):
    original=gc.get_threshold();enabled=gc.isenabled()
    if not enabled or original[0]<=0 or original[1]<=0:
        raise RuntimeError('expected enabled young generation collection')
    start=time.monotonic()
    gc.collect(2) # before original platform creates a live ROS/physics session
    counts=[x['collections'] for x in gc.get_stats()]
    gc.set_threshold(original[0],original[1],1_000_000)
    receipt.update(before=list(original),active=list(gc.get_threshold()),enabled=gc.isenabled(),
                   runtime_start_wall=time.monotonic(),precollect_wall_s=time.monotonic()-start)
    try:yield
    finally:
        receipt.update(collections=[x['collections']-n for x,n in zip(gc.get_stats(),counts)],
                       elapsed_wall_s=time.monotonic()-receipt['runtime_start_wall'],
                       peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       active_at_exit=list(gc.get_threshold()))
        gc.set_threshold(*original)
        receipt['restored']=gc.get_threshold()==original and gc.isenabled()==enabled

def main():
    if sys.version_info[:2]!=(3,12):raise RuntimeError('GC policy requires Python 3.12')
    from ch13_navigation_reuse.platform_adapter import main as native
    report=Path(sys.argv[sys.argv.index('--report')+1])
    receipt={'source':'CH15_DEFER_GEN2_V1','python':sys.version}
    try:
        with defer_full_collection(receipt):native()
    finally:
        # Original platform has closed its ROS and engine session before here.
        path=report.parent/'gc_policy_receipt.json'
        path.write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
