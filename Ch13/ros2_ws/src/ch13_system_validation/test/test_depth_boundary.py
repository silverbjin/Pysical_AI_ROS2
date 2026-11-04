"""Actual v9 rejected RGB-D: retain strict shape limits and reject edge bleed."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder


def capture():
    folder=Path(__file__).parent/'data/v9_depth_boundary'
    meta=json.loads((folder/'capture.json').read_text())
    return np.array(Image.open(folder/'rgb.png')),np.load(folder/'depth.npy'),meta


def test_raw_depth_boundary_outliers_do_not_hide_the_visible_known_cylinder():
    rgb,depth,meta=capture();args=(rgb,depth,meta['calibration'],meta['T_map_camera'],.02,.08)
    with pytest.raises(ValueError):fit_cylinder(*args)
    result=fit_cylinder(*args,filter_boundary=True)
    # Post-exit freejoint is used only for this assertion, never as fit input.
    np.testing.assert_allclose(result['center'],[1.799988,-.000028,.539891],atol=.0025)
    assert result['residual_m']<=.0015 and result['visible_height_m']>=.06
    assert result['boundary_filter']=='foreground_depth_consistency_3x3_5mm'
    assert result['boundary_removed_pixels']>0


def test_boundary_filter_still_refuses_a_single_short_fragment():
    rgb,depth,meta=capture();rgb[:135]=0
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,meta['calibration'],meta['T_map_camera'],.02,.08,filter_boundary=True)
