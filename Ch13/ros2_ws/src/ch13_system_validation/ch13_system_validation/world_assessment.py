"""Post-exit terrain/door witness; never grants live motion authority."""
import math


def assess_world(rows,scenario,*,found):
    if scenario.world=='empty':return dict(result='PASS',scope='legacy empty fixture; no extra world witness')
    try:
        points=[r['base_xyz'] for r in rows]
        assert len(points)>1 and all(len(p)==3 and all(math.isfinite(v) for v in p) for p in points)
        checks=dict(fresh_find=found is True)
        extra={}
        if scenario.world=='obstacles':
            force=max(r['ramp_contact_N'] for r in rows)
            assert math.isfinite(force) and force>=0
            checks.update(crossed_ramp=min(p[0] for p in points)<.45 and max(p[0] for p in points)>.95,
                          actual_ramp_contact=force>1.)
            extra['max_ramp_contact_N']=force
        else:
            crossings=[]
            for a,b in zip(points,points[1:]):
                if (a[0]-1.1)*(b[0]-1.1)<=0 and a[0]!=b[0]:
                    y=a[1]+(b[1]-a[1])*(1.1-a[0])/(b[0]-a[0])
                    crossings.append(y)
            checks.update(door_passage=any(-.35<y<.75 for y in crossings),
                target_below_table=scenario.target_xyz[2]+.04<.83
                    and 2.55<scenario.target_xyz[0]<3.45 and .5<scenario.target_xyz[1]<1.5)
            extra['door_crossing_y_m']=crossings
        return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                    scope='actual post-exit base/contact plus admitted fresh find',**extra)
    except (KeyError,TypeError,ValueError,AssertionError):
        return dict(result='FAIL',reason='missing or invalid actual world witness')
