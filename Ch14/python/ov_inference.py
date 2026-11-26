#!/usr/bin/env python3
import argparse
from pathlib import Path
from ch14_ai_common.ov_backend import OpenVinoBackend
from ch14_ai_common.yolo_lab import infer_image

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--onnx",type=Path,required=True);p.add_argument("--sha256",required=True)
    p.add_argument("--image",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--threads",type=int,default=2)
    a=p.parse_args()
    b=OpenVinoBackend(a.onnx,a.sha256,a.threads)
    print(b.settings)
    infer_image(b,a.image,a.output)
