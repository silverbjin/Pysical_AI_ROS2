"""Known upright cylinder fit from RGB-D surface samples, never object qpos."""
import math
import numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import label,binary_erosion


def _foreground_boundary(valid,depth):
    # Preserve true silhouette pixels: only reject foreground depth bleeding
    # into a red boundary, compared with the same frame's red neighbours.
    interior=binary_erosion(valid,structure=np.ones((3,3),dtype=bool),iterations=1)
    ys,xs=np.nonzero(valid&~interior)
    padded=np.pad(np.where(valid,depth,np.inf),1,constant_values=np.inf)
    windows=np.stack([padded[ys+dy+1,xs+dx+1] for dy in (-1,0,1) for dx in (-1,0,1)],axis=1)
    counts=np.isfinite(windows).sum(axis=1);windows.sort(axis=1);rows=np.arange(len(ys))
    median=(windows[rows,(counts-1)//2]+windows[rows,counts//2])/2
    bad=depth[ys,xs]<median-.005
    result=valid.copy();result[ys[bad],xs[bad]]=False
    return result,int(bad.sum())


def fit_cylinder(rgb,depth,calibration,transform,radius,height,*,filter_boundary=False):
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
    valid=mask&np.isfinite(depth)&(depth>.01)
    if filter_boundary:valid,boundary_removed=_foreground_boundary(valid,depth)
    labels,count=label(valid)
    sizes=np.bincount(labels.ravel());candidates=[];errors=[];merged_errors=[];components=[]
    if count>256:raise ValueError('cylinder excessive red components')
    for component in range(1,count+1):
        if sizes[component]<20:continue
        ys,xs=np.nonzero(labels==component)
        z=depth[ys,xs].astype(float)
        camera=np.column_stack(((xs-k[2])*z/k[0],(ys-k[3])*z/k[1],z))
        world=camera@T[:3,:3].T+T[:3,3]
        components.append((xs,ys,np.mean(world[:,:2],axis=0),float(world[:,2].min()),float(world[:,2].max())))
        try:
            candidate=_fit_component(depth,k,T,radius,height,xs,ys);candidate['components_used']=1;candidates.append(candidate)
        except ValueError as error:errors.append(str(error))
    if len(components)>16:raise ValueError('cylinder excessive significant components')
    # A gray occluder can split the same red side into upper/lower patches.
    # Merge only nearby axial patches, then require the same full height-span
    # and circle residual bounds. Separate red robot geometry is not merged.
    for index,first in enumerate(components):
        for second in components[index+1:]:
            if np.linalg.norm(first[2]-second[2])>radius:continue
            span=max(first[4],second[4])-min(first[3],second[3])
            if not .75*height<=span<=1.05*height:continue
            xs=np.concatenate((first[0],second[0]));ys=np.concatenate((first[1],second[1]))
            try:
                candidate=_fit_component(depth,k,T,radius,height,xs,ys);candidate['components_used']=2;candidates.append(candidate)
            except ValueError as error:merged_errors.append(str(error))
    unique=[]
    for candidate in sorted(candidates,key=lambda c:c['residual_m']):
        if not any(np.linalg.norm(np.array(candidate['center'])-other['center'])<=.002 for other in unique):unique.append(candidate)
    if len(unique)>1:raise ValueError('cylinder ambiguous matching components')
    if not candidates:
        if errors:raise ValueError('cylinder no matching component: '+(merged_errors[0] if filter_boundary and merged_errors else errors[0]))
        raise ValueError('cylinder not observed')
    result=unique[0];result.update(red_components=count,valid_cylinder_components=1)
    if filter_boundary:result.update(boundary_filter='foreground_depth_consistency_3x3_5mm',boundary_removed_pixels=boundary_removed)
    return result


def _fit_component(depth,k,T,radius,height,xs,ys):
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
