"""Pure command plans for the existing approved native validation profiles."""
import sys


def g1_plan(engine,output,prepared,scene,profile,clock,backend):
    if engine not in ('mujoco','gazebo'):raise ValueError('unknown validation engine')
    if clock not in ('native','relay100') or backend not in ('python','native_cdr'):
        raise ValueError('unknown execution profile')
    if engine=='gazebo' and clock!='relay100':
        raise ValueError('Gazebo validation profile requires explicit relay100')
    reference='g1_ramp20ms' if engine=='gazebo' else 'native'
    contact='allowance50um' if engine=='gazebo' else 'native'
    prepare=[sys.executable,'Ch13/scripts/prepare_navigation_model_13_5.py',
        '--scene-engine',engine,'--output-dir',str(prepared)]
    if engine=='gazebo':prepare+=['--g1-reference-ramp','--g1-contact-allowance']
    command=[sys.executable,'Ch13/scripts/run_navigation_13_5.py','--engine',engine,
        '--scenario','sensors-carry','--scene-dir',str(scene),'--profile',str(profile),
        '--output-dir',str(output),'--control-clock-mode',clock,'--observer-backend',backend,
        '--dart-contact-mode',contact]
    return dict(engine=engine,position_reference_mode=reference,dart_contact_mode=contact,
        prepare_command=prepare,command=command)


def validation_command(engine,root,pairs):
    if engine not in ('mujoco','gazebo') or pairs not in (1,3):
        raise ValueError('unknown engine or undeclared pair count')
    seed=('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/'
        'native-g1-mujoco-9d296bc8-1f99-494a-83f4-2bfc0bdc3751/result.json') if engine=='mujoco' else ''
    return ['bash',str(root/'timesync-comparison-user.sh'),str(root),seed,str(pairs),engine]
