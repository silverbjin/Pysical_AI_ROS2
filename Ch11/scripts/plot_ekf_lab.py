#!/usr/bin/env python3
"""Plot recorded relative planar errors; improvement is measured, not assumed."""
import argparse
import csv
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file')
    parser.add_argument('--output', required=True, help='PNG or PDF path')
    args = parser.parse_args()
    with open(args.csv_file, newline='') as stream:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    if not rows or any(not math.isfinite(v) for row in rows for v in row.values()):
        raise SystemExit('Empty or nonfinite comparison data')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit('Install python3-matplotlib before plotting.')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for name, label, color in (('truth', 'Gazebo reference', 'black'),
                               ('raw', 'Command odometry', '#e48322'),
                               ('filtered', 'EKF', '#2677bb')):
        axes[0].plot([r[name+'_x'] for r in rows], [r[name+'_y'] for r in rows],
                     label=label, color=color)
    axes[0].set(xlabel='Relative x (m)', ylabel='Relative y (m)',
                title='Recorded trajectories', aspect='equal')
    for name, color in (('raw', '#e48322'), ('filtered', '#2677bb')):
        axes[1].plot([r['t'] for r in rows], [r[name+'_error'] for r in rows],
                     label=name, color=color)
    axes[1].set(xlabel='Simulation time (s)', ylabel='Planar position error (m)',
                title='Error against recorded Gazebo reference')
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)
    metrics = {name+'_rmse_m': math.sqrt(sum(r[name+'_error']**2 for r in rows)/len(rows))
               for name in ('raw', 'filtered')}
    metrics.update(rows=len(rows), note='Relative planar error; EKF improvement is not guaranteed.')
    output.with_suffix('.metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
