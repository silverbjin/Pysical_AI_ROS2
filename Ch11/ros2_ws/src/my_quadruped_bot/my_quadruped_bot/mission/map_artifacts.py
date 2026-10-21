"""Read Nav2 trinary PGM/YAML outputs without claiming map accuracy."""
from pathlib import Path
import math
import yaml


def read_pgm(path):
    data = Path(path).read_bytes()
    i = 0
    def token():
        nonlocal i
        while i < len(data):
            if data[i:i+1] == b'#':
                end = data.find(b'\n', i)
                i = len(data) if end < 0 else end+1
            elif data[i:i+1].isspace():
                i += 1
            else:
                break
        start = i
        while i < len(data) and not data[i:i+1].isspace():
            i += 1
        return data[start:i]
    magic, width, height, maximum = token(), int(token()), int(token()), int(token())
    if magic not in (b'P5',b'P2') or width <= 0 or height <= 0 or maximum != 255:
        raise ValueError('Expected 8-bit PGM with positive dimensions')
    if magic == b'P5':
        if i >= len(data) or not data[i:i+1].isspace():
            raise ValueError('Missing PGM separator')
        i += 2 if data[i:i+2] == b'\r\n' else 1
        pixels = data[i:i+width*height]
        # Refuse extra P5 payload: image dimensions must match saved bytes.
        if len(data) - i != width*height:
            raise ValueError('PGM raster length does not match dimensions')
    else:
        pixels = bytes(int(token()) for _ in range(width*height))
    if len(pixels) != width*height:
        raise ValueError('Truncated PGM raster')
    return width, height, pixels


def analyze_map(yaml_path):
    path = Path(yaml_path)
    try:
        meta = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise ValueError('Malformed map YAML') from error
    resolution = float(meta['resolution'])
    origin = [float(v) for v in meta['origin']]
    if (not math.isfinite(resolution) or resolution <= 0 or len(origin) != 3
            or not all(math.isfinite(v) for v in origin) or meta.get('mode','trinary') != 'trinary'):
        raise ValueError('Invalid map metadata or unsupported map mode')
    image = Path(meta['image'])
    if not image.is_absolute():
        image = path.parent/image
    width,height,pixels = read_pgm(image)
    counts = {'occupied_black': pixels.count(0),
              'free_light': pixels.count(254)+pixels.count(255),
              'unknown_gray': pixels.count(205)}
    counts['other_pixels'] = len(pixels)-sum(counts.values())
    return {'yaml':str(path.resolve()),'image':str(image.resolve()), 'width':width,'height':height,
            'resolution':resolution,'origin':origin,'bounds_area_m2':width*height*resolution**2,
            'pixel_counts':counts,'quality_verified':False,
            'note':'Rendered trinary classes only; not full coverage or geometric accuracy.'}
