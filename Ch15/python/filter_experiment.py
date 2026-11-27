"""C20 synthetic LPF exercise, explicitly not a physical sensor benchmark."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def finite(x):return type(x) in (int,float) and math.isfinite(x)
class LowPassFilter:
    def __init__(self,alpha):
        if not finite(alpha) or not 0<alpha<=1:raise ValueError('invalid alpha')
        self.alpha=float(alpha);self.reset()
    def reset(self):
        self.value=None;self.stamp=None
    def filter(self,raw_val,stamp=None):
        if not finite(raw_val) or (stamp is not None and not finite(stamp)):
            raise ValueError('invalid sample')
        if self.stamp is not None and stamp is not None and stamp<=self.stamp:
            if stamp<self.stamp:self.reset()
            raise ValueError('nonadvancing time')
        self.value=float(raw_val) if self.value is None else self.alpha*raw_val+(1-self.alpha)*self.value
        if stamp is not None:self.stamp=stamp
        return self.value

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    t=np.arange(1,801)/200.;truth=np.sin(2*np.pi*t);raw=truth+np.random.default_rng(15).normal(0,.2,800)
    lpf=LowPassFilter(.2);filtered=np.array([lpf.filter(float(x),float(s)) for s,x in zip(t,raw)])
    rmse=lambda x:float(np.sqrt(np.mean((x-truth)**2)))
    lag=int(np.argmax(np.correlate(filtered-filtered.mean(),truth-truth.mean(),mode='full'))-(len(t)-1))
    with (out/'filter.csv').open('x',newline='') as f:
        w=csv.writer(f);w.writerow(['sim_s','truth','raw','filtered']);w.writerows(zip(t,truth,raw,filtered))
    fig,ax=plt.subplots(figsize=(9,4.8));ax.plot(t,raw,alpha=.45,label='raw noisy');ax.plot(t,truth,label='truth');ax.plot(t,filtered,label='LPF');ax.set(xlabel='time (s)',ylabel='signal');ax.legend();ax.grid(True,alpha=.25);fig.tight_layout();fig.savefig(out/'filter.png',dpi=130);plt.close(fig)
    result=dict(result='PASS' if rmse(filtered)<rmse(raw) else 'FAIL',source='SYNTHETIC',samples=800,seed=15,alpha=.2,noise_sigma=.2,raw_rmse=rmse(raw),filtered_rmse=rmse(filtered),lag_samples=lag,lag_s=lag/200.)
    (out/'filter_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
