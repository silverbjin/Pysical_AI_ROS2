#!/usr/bin/env python3
"""Real saved-image YOLO smoke, not an engine-recognition/accuracy benchmark."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import time
import uuid


def run(weights: Path, image: Path, manifest: Path, output: Path, annotation_dir=None):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(status='RUNNING', run_id=str(uuid.uuid4()), started_at=time.time(),
                  backend='yolo', test_kind='saved_image_smoke', errors=[])

    def save():
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    save()
    start = time.perf_counter()
    try:
        if not Path(weights).is_file() or not Path(image).is_file():
            raise FileNotFoundError('explicit local weights and image are required')
        import cv2
        from integrated_robot_vision.detectors import YoloBackend, verify_asset
        metadata = json.loads(Path(manifest).read_text(encoding='utf-8'))['assets']
        verify_asset(Path(weights), metadata['yolov8n.pt']['sha256'])
        verify_asset(Path(image), metadata['bus.jpg']['sha256'])
        bgr = cv2.imread(str(image))
        if bgr is None:
            raise ValueError('image decode failed')
        load_start = time.perf_counter()
        backend = YoloBackend(Path(weights), expected_sha256=metadata['yolov8n.pt']['sha256'])
        result['model_load_s'] = time.perf_counter() - load_start
        inference_start = time.perf_counter()
        boxes = backend.detect(bgr)
        from ultralytics.utils import AUTOINSTALL
        result['inference_s'] = time.perf_counter() - inference_start
        result['versions'] = {name: version(name) for name in
                              ('ultralytics', 'torch', 'torchvision', 'numpy', 'opencv-python')}
        result['weights_sha256'], result['image_sha256'] = (
            metadata['yolov8n.pt']['sha256'], metadata['bus.jpg']['sha256'])
        result['detections'] = [dict(class_id=v.class_id, class_name=backend.class_names.get(int(v.class_id)),
                                      score=v.score, xywh=[v.cx, v.cy, v.width, v.height]) for v in boxes]
        # Keep the third-party photo and its annotated derivative out of Git.
        annotation_dir = Path(annotation_dir) if annotation_dir else Path(image).resolve().parent / 'annotations'
        annotation_dir.mkdir(parents=True, exist_ok=True)
        annotation = annotation_dir / f'bus-yolo-{result["run_id"]}.png'
        for box in boxes:
            x0, y0 = round(box.cx-box.width/2), round(box.cy-box.height/2)
            x1, y1 = round(box.cx+box.width/2), round(box.cy+box.height/2)
            cv2.rectangle(bgr, (x0, y0), (x1, y1), (0, 255, 0), 2)
            cv2.putText(bgr, f'{box.class_id} {box.score:.2f}', (x0, max(15, y0)),
                        cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 2)
        if not cv2.imwrite(str(annotation), bgr):
            raise RuntimeError('annotation write failed')
        result['annotation'] = dict(path=str(annotation.resolve()),
                                     sha256=hashlib.sha256(annotation.read_bytes()).hexdigest(),
                                     redistributed=False)
        result['checks'] = dict(actual_yolo=True, bus_class_5=any(v.class_id == '5' and v.score >= .5 for v in boxes),
                                 weights_hash_verified=True, image_hash_verified=True,
                                 sdk_autoinstall_disabled=not AUTOINSTALL)
        if not all(result['checks'].values()):
            failed = [name for name, passed in result['checks'].items() if not passed]
            raise RuntimeError('YOLO smoke checks failed: ' + ', '.join(failed))
        result['status'] = 'PASS'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['errors'].append(repr(exc))
    finally:
        result['duration_s'] = time.perf_counter() - start
        result['finished_at'] = time.time()
        save()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--annotation-dir')
    parser.add_argument('--manifest', default=str(Path(__file__).resolve().parents[1] / 'config/vision_assets.json'))
    args = parser.parse_args()
    result = run(Path(args.weights), Path(args.image), Path(args.manifest), Path(args.output), args.annotation_dir)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
