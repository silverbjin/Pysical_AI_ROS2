"""Service success is insufficient: pin the actual rejected north route."""
import json
from pathlib import Path
from ch13_navigation_reuse.path_geometry import path_footprint_clear

DATA=json.loads((Path(__file__).parent/'data/heading_path_footprints.json').read_text())

def test_actual_heading_path_audit_rejects_interior_collision_and_accepts_west():
    assert path_footprint_clear(DATA['valid_path'],DATA['grid'],DATA['footprint'])
    assert not path_footprint_clear(DATA['invalid_path'],DATA['grid'],DATA['footprint'])

def test_empty_nonfinite_and_unbounded_paths_are_not_executable():
    for value in ([],[[float('nan'),1.,0.]],DATA['valid_path']*2049):
        assert not path_footprint_clear(value,DATA['grid'],DATA['footprint'])
