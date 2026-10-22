"""Verify downloaded bytes before publishing an asset; never replace bad cache."""
import importlib.util
import io
from pathlib import Path

import pytest


def loader():
    path = Path(__file__).resolve().parents[1] / 'scripts/fetch_vision_assets.py'
    spec = importlib.util.spec_from_file_location('asset_fetch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def asset_spec():
    return dict(url='https://raw.githubusercontent.com/ultralytics/ultralytics/v8.3.221/ultralytics/assets/bus.jpg',
                sha256='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
                size_bytes=3)


def test_verified_download_is_published_and_bad_cache_is_not_overwritten(tmp_path):
    module = loader()
    destination = tmp_path / 'bus.jpg'
    result = module.fetch_asset(asset_spec(), destination, opener=lambda *_a, **_k: io.BytesIO(b'abc'))
    assert result == destination and destination.read_bytes() == b'abc'
    destination.write_bytes(b'bad-cache')
    with pytest.raises(ValueError):
        module.fetch_asset(asset_spec(), destination, opener=lambda *_a, **_k: io.BytesIO(b'abc'))
    assert destination.read_bytes() == b'bad-cache'


def test_corrupt_download_and_untrusted_url_never_publish(tmp_path):
    module = loader()
    destination = tmp_path / 'bus.jpg'
    with pytest.raises(ValueError):
        module.fetch_asset(asset_spec(), destination, opener=lambda *_a, **_k: io.BytesIO(b'xyz'))
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []
    spec = asset_spec() | {'url': 'https://untrusted.invalid/model.pt'}
    with pytest.raises(ValueError):
        module.fetch_asset(spec, destination)


def test_yolo_probe_missing_assets_overwrites_old_pass_with_fresh_failure(tmp_path):
    import json
    import subprocess
    import sys
    output = tmp_path / 'result.json'
    output.write_text(json.dumps({'status': 'PASS', 'run_id': 'old'}))
    script = Path(__file__).resolve().parents[1] / 'scripts/verify_yolo_13_4.py'
    run = subprocess.run([sys.executable, str(script), '--weights', str(tmp_path / 'missing.pt'),
                          '--image', str(tmp_path / 'missing.jpg'), '--output', str(output)],
                         capture_output=True, text=True, timeout=15)
    assert run.returncode != 0
    result = json.loads(output.read_text())
    assert result['status'] == 'FAIL'
    assert result['run_id'] != 'old'
    assert result['errors']
