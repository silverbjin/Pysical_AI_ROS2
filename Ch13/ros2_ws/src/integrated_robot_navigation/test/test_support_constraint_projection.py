"""Body-support feasibility may exist between the old centroid/vertex rays."""
import numpy as np
import pytest
from integrated_robot_navigation import support


def test_off_ray_solution_satisfies_support_and_collision_halfplanes():
    assert hasattr(support,'nearest_halfplane_point'),'bounded 2D constraint projection missing'
    # x must move rearward, y must remain below the collision boundary. The
    # nearest valid point lies on the intersection, not a selected search ray.
    matrix=np.array([[-.5,1.],[0.,-1.]])
    bounds=np.array([.055,-.02])
    result=support.nearest_halfplane_point(matrix,bounds)
    assert np.allclose(result,[-.07,.02],atol=1e-12)
    assert np.all(matrix@result>=bounds-1e-12)


def test_inconsistent_constraints_are_rejected_without_an_approximate_target():
    assert hasattr(support,'nearest_halfplane_point'),'bounded 2D constraint projection missing'
    with pytest.raises(ValueError,match='infeasible'):
        support.nearest_halfplane_point(np.array([[1.,0.],[-1.,0.]]),np.array([1.,1.]))
