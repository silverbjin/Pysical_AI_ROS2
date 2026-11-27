import py_trees
def create_root(profile,tasks):
    if profile=='physical_full':raise ValueError('PHYSICAL_FULL_BLOCKED')
    if profile not in ('mock','physical_basic'):raise ValueError('unknown profile')
    required=('fault_latched','safe_abort','ready','navigate','detect','approach_stand','pick_retract','return_home','place','verify_finish')
    if any(k not in tasks for k in required):raise ValueError('missing task')
    safety=py_trees.composites.Sequence(name='Safety',memory=False,children=[tasks['fault_latched'],tasks['safe_abort']])
    order=['ready','navigate','detect','approach_stand']
    if profile=='mock':order+=['pick_retract','return_home','place']
    order+=['verify_finish']
    mission=py_trees.composites.Sequence(name='Mission',memory=True,children=[tasks[k] for k in order])
    return py_trees.composites.Selector(name='Root',memory=False,children=[safety,mission])
