"""Common YOLOv8 COCO FP32 letterbox and deterministic class-wise NMS."""
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class Letterbox:
    sx: float
    sy: float
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class Detection:
    class_id: int
    confidence: float
    xyxy: tuple[float, float, float, float]


def preprocess(bgr, size=640):
    if (not isinstance(bgr, np.ndarray) or bgr.dtype != np.uint8 or
            bgr.ndim != 3 or bgr.shape[2] != 3 or min(bgr.shape[:2]) <= 0 or
            size != 640):
        raise ValueError('nonempty uint8 BGR HWC and fixed size 640 required')
    h, w = bgr.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = round(w * scale), round(h * scale)
    if min(nw, nh) < 1:
        raise ValueError('image aspect ratio cannot be represented')
    left, top = (size - nw) // 2, (size - nh) // 2
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    canvas[top:top + nh, left:left + nw] = cv2.resize(bgr, (nw, nh))
    x = np.ascontiguousarray(canvas[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32)
    x /= np.float32(255.)
    return x, Letterbox(nw / w, nh / h, left, top, w, h)


def _iou(one, many):
    extent = np.maximum(0., np.minimum(one[2:], many[:, 2:]) - np.maximum(one[:2], many[:, :2]))
    inter = extent[:, 0] * extent[:, 1]
    union = np.prod(one[2:] - one[:2]) + np.prod(many[:, 2:] - many[:, :2], axis=1) - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)


def postprocess(out, meta, conf=0.5, iou=0.45):
    if not all(np.isfinite(v) and 0 <= v <= 1 for v in (conf, iou)):
        raise ValueError('invalid threshold')
    if not isinstance(meta, Letterbox) or not all(np.isfinite(v) and v > 0 for v in (meta.sx, meta.sy, meta.width, meta.height)):
        raise ValueError('invalid letterbox metadata')
    if (not isinstance(out, np.ndarray) or out.dtype != np.float32 or
            out.shape != (1, 84, 8400) or not np.isfinite(out).all()):
        raise ValueError('expected finite FP32 YOLO output (1,84,8400)')
    pred = out[0].T
    classes = pred[:, 4:].argmax(axis=1)
    scores = pred[np.arange(len(pred)), 4 + classes]
    if np.any(scores < 0) or np.any(scores > 1):
        raise ValueError('invalid class score')
    ids = np.flatnonzero((scores >= conf) & (pred[:, 2] > 0) & (pred[:, 3] > 0))
    # Reject zero-score boxes even at conf=0; they carry no evidence.
    ids = ids[scores[ids] > 0]
    boxes = pred[:, :4].astype(np.float64)
    xyxy = np.column_stack((boxes[:, :2] - boxes[:, 2:] / 2, boxes[:, :2] + boxes[:, 2:] / 2))
    keep = []
    for cls in np.unique(classes[ids]):
        pool = ids[classes[ids] == cls]
        pool = pool[np.argsort(-scores[pool], kind='stable')]
        while len(pool):
            selected = pool[0]
            keep.append(int(selected))
            pool = pool[1:]
            pool = pool[_iou(xyxy[selected], xyxy[pool]) <= iou]
    result = []
    for k in sorted(keep, key=lambda j: (-float(scores[j]), j)):
        x1, y1, x2, y2 = xyxy[k]
        x1, x2 = np.clip((np.array([x1, x2]) - meta.left) / meta.sx, 0, meta.width)
        y1, y2 = np.clip((np.array([y1, y2]) - meta.top) / meta.sy, 0, meta.height)
        if x2 > x1 and y2 > y1:
            result.append(Detection(int(classes[k]), float(scores[k]), tuple(map(float, (x1, y1, x2, y2)))))
    return result
