def validate_options(backend='mujoco',enabled=False,headless=True,world='',seed=42):
    if backend not in ('mujoco','gazebo'):raise ValueError('backend must be mujoco or gazebo')
    return dict(backend=backend,enabled=enabled,headless=headless,world=world,seed=int(seed))
