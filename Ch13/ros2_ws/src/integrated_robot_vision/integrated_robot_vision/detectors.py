"""Explicit local model loading; fixture detection is a separate backend."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re

import cv2
import numpy as np

from .contracts import Box2D


def verify_asset(path: Path, expected_sha256: str) -> None:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'explicit existing asset required: {path}')
    if not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('recorded SHA256 required before model loading')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(128*1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256:
        raise ValueError('asset SHA256 mismatch')


def bgr8(image):
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
            or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) <= 0):
        raise ValueError('nonempty uint8 HxWx3 BGR image required')
    return np.ascontiguousarray(image)


def clip_box(box, size):
    if size is None:
        return box
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError('positive image dimensions required')
    x0, x1 = max(0., box.cx-box.width/2), min(float(width), box.cx+box.width/2)
    y0, y1 = max(0., box.cy-box.height/2), min(float(height), box.cy+box.height/2)
    if x1 <= x0 or y1 <= y0:
        return None
    return Box2D((x0+x1)/2, (y0+y1)/2, x1-x0, y1-y0, box.class_id, box.score)


class ColorFixtureBackend:
    """Red component geometry only, never a semantic YOLO substitute.

    Component centers are inclusive pixel-center means, (min+max)/2;
    widths/heights are the inclusive pixel count. This yields center29.5
    and width20 for pixel indices20..39, as used by the depth pixel lookup.
    """

    def detect(self, bgr: np.ndarray) -> list[Box2D]:
        image = bgr8(bgr).astype(np.int16)
        blue, green, red = image[:, :, 0], image[:, :, 1], image[:, :, 2]
        mask = ((red > 80) & (red > 1.5*green) & (red > 1.5*blue)).astype(np.uint8)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        boxes = []
        for x, y, width, height, area in stats[1:count]:
            if area >= 20:
                boxes.append(Box2D(float(x+(width-1)/2), float(y+(height-1)/2),
                                   float(width), float(height), 'fixture_red', 1.))
        return boxes


def official_model_sha():
    from ament_index_python.packages import get_package_share_directory
    path = Path(get_package_share_directory('integrated_robot_vision')) / 'config/vision_assets.json'
    return json.loads(path.read_text(encoding='utf-8'))['assets']['yolov8n.pt']['sha256']


class YoloBackend:
    def __init__(self, weights: Path, device: str = 'cpu', expected_sha256=None):
        weights = Path(weights)
        if not weights.is_file():
            raise FileNotFoundError(f'explicit local weights required: {weights}')
        if device != 'cpu':
            raise ValueError('this reproducible lab supports device=cpu only')
        verify_asset(weights, expected_sha256 if expected_sha256 is not None else official_model_sha())
        # No implicit remote model name, node-time download or fixture fallback.
        os.environ['YOLO_AUTOINSTALL'] = 'false'
        from ultralytics import YOLO
        from ultralytics.utils import AUTOINSTALL
        if AUTOINSTALL:
            raise RuntimeError('SDK already imported with autoinstall enabled; use a fresh process')
        import torch
        torch.set_num_threads(1)
        self.model = YOLO(str(weights.resolve()), task='detect')
        self.class_names = dict(self.model.names)

    def detect(self, bgr: np.ndarray) -> list[Box2D]:
        image = bgr8(bgr)
        results = self.model.predict(image, device='cpu', imgsz=320, conf=.5,
                                     verbose=False, save=False)
        if not results or results[0].boxes is None:
            return []
        detections = results[0].boxes
        boxes = []
        for xywh, cls, score in zip(detections.xywh.cpu().numpy(),
                                     detections.cls.cpu().tolist(), detections.conf.cpu().tolist()):
            box = clip_box(Box2D(*map(float, xywh), str(int(cls)), float(score)),
                           (image.shape[1], image.shape[0]))
            if box is not None:
                boxes.append(box)
        return boxes


def to_detection_array(boxes: list[Box2D], header, image_size=None):
    from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
    result = Detection2DArray()
    result.header = deepcopy(header)
    for box in boxes:
        box = clip_box(box, image_size)
        if box is None:
            continue
        detection = Detection2D()
        detection.header = deepcopy(header)
        detection.bbox.center.position.x, detection.bbox.center.position.y = box.cx, box.cy
        detection.bbox.size_x, detection.bbox.size_y = box.width, box.height
        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id, hypothesis.hypothesis.score = box.class_id, box.score
        # Pose fields are not a 3D pose estimate; fusion uses only box/class/score.
        detection.results = [hypothesis]
        result.detections.append(detection)
    return result
