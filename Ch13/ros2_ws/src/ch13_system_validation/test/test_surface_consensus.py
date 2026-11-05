"""Real rejected image and adverse geometry, without oracle fit inputs."""
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from scipy.ndimage import label
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder


def frame(fixture='v13_surface_outliers'):
    folder=Path(__file__).parent/'data'/fixture
    meta=json.loads((folder/'capture.json').read_text())
    return np.array(Image.open(folder/'rgb.png')),np.load(folder/'depth.npy'),meta['calibration'],np.array(meta['T_map_camera'])


@pytest.mark.parametrize('fixture',['v9_depth_boundary','v13_surface_outliers'])
def test_actual_sparse_surface_outliers_are_segmented_before_strict_inlier_fit(fixture):
    args=frame(fixture)
    with pytest.raises(ValueError):fit_cylinder(*args,.02,.08)
    result=fit_cylinder(*args,.02,.08,robust_consensus=True)
    # Truth is post-fit grading only; it is never supplied to the estimator.
    np.testing.assert_allclose(result['center'],[1.8,0.,.54],atol=.002)
    assert result['raw_residual_m']>.0015
    assert result['residual_m']<.0015 and result['surface_inlier_fraction']>=.95
    assert result['outlier_points']>0 and result['visible_height_m']>=.06


def test_widespread_corruption_cannot_be_hidden_by_inlier_refinement():
    rgb,depth,k,T=frame()
    ys,xs=np.nonzero((rgb[:,:,0]>80)&np.isfinite(depth))
    depth[ys[::4],xs[::4]]-=.04
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,k,T,.02,.08,robust_consensus=True)


def test_consensus_preserves_historical_transform_and_height_requirement():
    rgb,depth,k,T=frame();T[:3,3]+=[1.,-.2,.3]
    result=fit_cylinder(rgb,depth,k,T,.02,.08,robust_consensus=True)
    np.testing.assert_allclose(result['center'],[2.8,-.2,.84],atol=.002)
    ys,_=np.nonzero(rgb[:,:,0]>80)
    rgb[:(ys.min()+ys.max())//2]=0
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,k,T,.02,.08,robust_consensus=True)


def test_actual_small_occlusion_fragment_is_kept_until_combined_model_validation():
    args=frame('v18_small_fragment')
    with pytest.raises(ValueError,match='height visibility'):fit_cylinder(*args,.02,.08)
    result=fit_cylinder(*args,.02,.08,robust_consensus=True)
    np.testing.assert_allclose(result['center'],[2.,0.,.039857847],atol=.002)
    assert result['components_used']==2
    assert result['surface_inlier_fraction']>=.95 and result['visible_height_m']>=.06


def test_small_fragment_cannot_replace_visible_height_or_stand_alone():
    rgb,depth,k,T=frame('v18_small_fragment')
    color=rgb.astype(float)
    labels,count=label((color[:,:,0]>80)&(color[:,:,0]>1.8*color[:,:,1])&(color[:,:,0]>1.8*color[:,:,2]))
    sizes=np.bincount(labels.ravel());small=np.flatnonzero((sizes>0)&(sizes<20))
    assert len(small)==1 and sizes[small[0]]==13
    for keep in (labels!=small[0],labels==small[0]):
        image=rgb.copy();image[~keep]=0
        with pytest.raises(ValueError):fit_cylinder(image,depth,k,T,.02,.08,robust_consensus=True)


def test_unrelated_small_red_patch_is_not_merged_into_cylinder():
    rgb,depth,k,T=frame('v18_small_fragment')
    rgb[20:23,20:23]=[230,0,0];depth[20:23,20:23]=.1
    result=fit_cylinder(rgb,depth,k,T,.02,.08,robust_consensus=True)
    np.testing.assert_allclose(result['center'],[2.,0.,.039857847],atol=.002)
    assert result['components_used']==2
