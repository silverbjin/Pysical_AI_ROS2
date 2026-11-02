#!/usr/bin/env python3
"""Real, offline CPU-budget regression using an explicitly supplied native frame."""
import argparse
import json
from pathlib import Path
import time

import cv2
from integrated_robot_vision.detectors import YoloBackend
from verify_vision_13_4 import EvidenceRun, source_snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    with EvidenceRun(args.output_dir, {'actual_inference', 'one_cpu_thread'}) as run:
        image = cv2.imread(args.image)
        if image is None:
            raise ValueError('explicit readable native image required')
        run.result['image_path'] = str(Path(args.image).resolve())
        run.result['image_size'] = list(image.shape)
        run.result['source'] = source_snapshot(Path(__file__).resolve().parents[2])
        backend = YoloBackend(Path(args.weights))
        import torch
        rows = []
        for index in range(3):
            started = time.monotonic()
            boxes = backend.detect(image)
            rows.append(dict(index=index, elapsed_s=time.monotonic()-started,
                threads=torch.get_num_threads(),
                detections=[dict(class_id=v.class_id, confidence=v.score) for v in boxes]))
        path = run.root/'measurements.json'
        path.write_text(json.dumps(rows, indent=2)+'\n', encoding='utf-8')
        run.artifact(path)
        run.result['inference'] = rows
        run.result['scope'] = 'offline native frame, not live camera latency or semantic success'
        try:
            run.finish(dict(actual_inference=len(rows) == 3, one_cpu_thread=all(v['threads'] == 1 for v in rows)))
        except RuntimeError:
            pass
    print(json.dumps(dict(status=run.result['status'], measurements=rows), indent=2))
    return 0 if run.result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
