import json
import os
from pathlib import Path
import sys
import uuid
sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
from verify_all_13_4 import run_command, check_engine_continuation

root = Path(os.environ['CH13_EGL_EVIDENCE'])
def live_engines():
    found = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            argv = (process/'cmdline').read_bytes().decode(errors='replace').split('\0')
            state = (process/'stat').read_text().split(') ',1)[1].split()[0]
            if state != 'Z' and (Path(argv[0]).name in ('ros2_control_node','gz','gzserver')
                    or (any(Path(a).name == 'gz' for a in argv) and 'sim' in argv)
                    or any('gz-sim-server' in a for a in argv)):
                found.append(dict(pid=int(process.name),argv=argv))
        except (OSError,IndexError):
            pass
    return found

for engine in ('mujoco', 'gazebo'):
    before = live_engines()
    if before:
        raise RuntimeError('Existing engine; no signals sent: '+repr(before))
    output = root/('legacy_'+engine)
    if output.exists():
        raise FileExistsError(output)
    native = output/'native'
    print('START legacy_'+engine, flush=True)
    command = [sys.executable,'Ch13/scripts/run_architecture_13_3.py',
               '--engine',engine,'--output-dir',str(native)]
    value = run_command('legacy_'+engine,command,output=output,batch_run_id=str(uuid.uuid4()),
                        cwd=Path.cwd(),kind='legacy',result_path=native/'result.json')
    after = live_engines()
    (output/'residual-observation.json').write_text(json.dumps(dict(live_engines_after=after),indent=2)+'\n')
    with (root/'legacy-progress.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(label='legacy_'+engine,status=value['status'],
                                      run_id=value['run_id'],checks=value['checks'],
                                      cleanup_confirmed=not after))+'\n')
    print(json.dumps(dict(label='legacy_'+engine,status=value['status'],checks=value['checks'])),flush=True)
    if after:
        raise RuntimeError('Live engine remains; refuse another engine without signaling unrelated PIDs')
    check_engine_continuation('legacy',value)
