"""Plot saved play/goal-demo CSV without connecting separate episodes."""
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    rows = np.atleast_1d(np.genfromtxt(args.csv,delimiter=',',names=True))
    required = {'episode','x','y','target_x','target_y'}
    if not required <= set(rows.dtype.names or ()) or not len(rows):
        parser.error('Input must be a nonempty play/goal-demo CSV')
    figure,axis = plt.subplots(figsize=(7,5),layout='constrained')
    for episode in np.unique(rows['episode']):
        selected = rows[rows['episode']==episode]
        axis.plot(selected['x'],selected['y'],label=f'Episode {int(episode)}')
        axis.scatter(selected['x'][0],selected['y'][0],marker='o',s=25,color='green')
    targets = np.unique(np.column_stack([rows['target_x'],rows['target_y']]),axis=0)
    targets = targets[np.isfinite(targets).all(axis=1)]
    if len(targets):
        axis.scatter(targets[:,0],targets[:,1],marker='x',color='red',label='Goal')
    axis.set(xlabel='World x [m]',ylabel='World y [m]',title='Measured rollout trajectory')
    axis.axis('equal')
    axis.grid(alpha=.3)
    axis.legend()
    figure.savefig(args.output,dpi=160)
    plt.close(figure)


if __name__ == '__main__':
    main()
