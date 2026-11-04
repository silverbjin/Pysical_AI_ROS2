"""Post-exit physical grading. Never import this as live mission authority."""
import math


def assess_transport(rows):
    try:
        carry=[r for r in rows if r['phase']=='CARRY']
        placed=[r for r in rows if r['phase']=='RETREAT']
        if len(carry)<2 or len(placed)<2:raise ValueError('carry and post-release evidence required')
        if any(not math.isfinite(r['sim_s']) for r in rows) or any(b['sim_s']<=a['sim_s'] for a,b in zip(rows,rows[1:])):
            raise ValueError('nonadvancing physical time')
        if any(len(r['target'])!=3 or not all(math.isfinite(v) for v in r['target']+r['relative_tcp']) for r in rows):
            raise ValueError('invalid physical coordinates')
        baseline=carry[0]['target'][2]
        dual=sum(all(r['target_contact_N'].get(f,0.)>.005 for f in ('link7','link8')) for r in carry)/len(carry)
        displacement=math.dist(carry[0]['target'][:2],carry[-1]['target'][:2])
        supported=all(r.get('target_support_N',0.)>.01 for r in placed)
        released=all(max(r['target_contact_N'].values(),default=0.)<.005 for r in placed)
        checks=dict(carry_displacement=displacement>.10,carry_contact_fraction=dual>=.9,
            carry_height=min(r['target'][2] for r in carry)>=baseline-.02,
            receiving_position=all(math.dist(r['target'][:2],[-.55,0.])<.03 for r in placed),
            receiving_height=all(abs(r['target'][2]-.54)<.005 for r in placed),
            supported=supported,released=released,placed_hold=placed[-1]['sim_s']-placed[0]['sim_s']>=2.)
        return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                    carry_displacement_m=displacement,dual_contact_fraction=dual,
                    scope='offline engine freejoint/contact evidence only')
    except (KeyError,TypeError,ValueError,IndexError) as error:
        return dict(result='FAIL',reason=str(error))
