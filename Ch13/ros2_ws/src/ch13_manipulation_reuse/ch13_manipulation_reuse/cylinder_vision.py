"""Known upright cylinder fit from RGB-D surface samples, never object qpos."""
import math
import numpy as np
from scipy.optimize import least_squares


def fit_cylinder(rgb,depth,calibration,transform,radius,height):
    if np.shape(rgb)!=(240,320,3) or np.shape(depth)!=(240,320):
        raise ValueError('cylinder calibrated320x240 RGB-D required')
    k=np.asarray(calibration,dtype=float);T=np.asarray(transform,dtype=float)
    if (k.shape!=(4,) or not np.isfinite(k).all() or min(k[:2])<=0
            or T.shape!=(4,4) or not np.isfinite(T).all()
            or not np.allclose(T[:3,:3].T@T[:3,:3],np.eye(3),atol=1e-5)
            or not math.isfinite(radius) or not math.isfinite(height) or min(radius,height)<=0):
        raise ValueError('cylinder invalid calibration/shape prior')
    color=rgb.astype(float)
    mask=(color[:,:,0]>80)&(color[:,:,0]>1.8*color[:,:,1])&(color[:,:,0]>1.8*color[:,:,2])
    ys,xs=np.nonzero(mask&np.isfinite(depth)&(depth>.01))
    if len(xs)<20:raise ValueError('cylinder not observed')
    z=depth[ys,xs].astype(float)
    camera=np.column_stack(((xs-k[2])*z/k[0],(ys-k[3])*z/k[1],z))
    world=camera@T[:3,:3].T+T[:3,3]
    low,high=np.quantile(world[:,2],[.01,.99]);span=high-low
    if not .75*height<=span<=1.05*height:raise ValueError('cylinder insufficient upright height visibility')
    # Visible caps lie near extremal world-z planes. Exclude those planes before
    # fitting the side circle so a bottom cap during lift cannot bias the center.
    side=world[(world[:,2]>low+.002)&(world[:,2]<high-.002)]
    if len(side)<20 or max(np.ptp(side[:,:2],axis=0))<radius:
        raise ValueError('cylinder insufficient side visibility')
    mean=np.mean(side[:,:2],axis=0);view=mean-T[:2,3]
    if np.linalg.norm(view)<radius:raise ValueError('cylinder camera inside target prior')
    view/=np.linalg.norm(view)
    def residual(center):return np.linalg.norm(side[:,:2]-center,axis=1)-radius
    result=least_squares(residual,mean+view*radius,loss='soft_l1',f_scale=.001,max_nfev=40)
    error=float(np.sqrt(np.mean(residual(result.x)**2)))
    if (not result.success or error>.0015 or np.quantile(abs(residual(result.x)),.9)>.002
            or np.dot(result.x-mean,view)<=0):
        raise ValueError('cylinder surface fit rejected')
    center=np.array([*result.x,(low+high)/2])
    optical=T[:3,:3].T@(center-T[:3,3])
    return dict(center=center.tolist(),optical_center=optical.tolist(),residual_m=error,points=len(side),
                visible_height_m=float(span),radius_prior_m=radius,height_prior_m=height,
                axis=[0.,0.,1.],axis_source='upright task prior',yaw_observed=False,
                box=dict(cx=float((xs.min()+xs.max())/2),cy=float((ys.min()+ys.max())/2),
                         width=float(xs.max()-xs.min()+1),height=float(ys.max()-ys.min()+1)))
