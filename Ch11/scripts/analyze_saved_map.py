#!/usr/bin/env python3
"""Summarize saved trinary map bytes and optionally render an annotated preview."""
import argparse
import json
from pathlib import Path
import sys

PKG=Path(__file__).resolve().parents[1]/'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0,str(PKG))
from my_quadruped_bot.mission.map_artifacts import analyze_map, read_pgm


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map_yaml',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--preview',type=Path)
    args=parser.parse_args()
    report=analyze_map(args.map_yaml)
    text=json.dumps(report,indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+'\n')
    if args.preview:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        width,height,pixels=read_pgm(report['image'])
        fig,ax=plt.subplots(figsize=(8,8))
        # Pixel row 0 is the top of the saved image; do not mirror it vertically.
        ax.imshow(np.frombuffer(pixels,dtype=np.uint8).reshape(height,width),cmap='gray',vmin=0,vmax=255)
        ax.set_title(f'Saved SLAM map | {report["resolution"]:.3f} m/pixel')
        ax.set_xlabel('image column (pixels)');ax.set_ylabel('image row (pixels)')
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(args.preview,dpi=160,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':main()
