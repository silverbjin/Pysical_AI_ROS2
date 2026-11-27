import argparse,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def plot(folder):
    with (folder/'states.csv').open() as f:rows=list(csv.DictReader(f))
    states=list(dict.fromkeys(r['state'] for r in rows))
    fig,ax=plt.subplots(figsize=(9,3.8))
    ax.step([float(r['elapsed_record_s']) for r in rows],[states.index(r['state']) for r in rows],where='post')
    ax.set(yticks=list(range(len(states))),yticklabels=states,xlabel='Record elapsed (s)',title='MOCK mission state (not physical)')
    ax.grid(axis='x',alpha=.3);fig.tight_layout();fig.savefig(folder/'mission.png',dpi=150);plt.close(fig)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);plot(p.parse_args().folder)
