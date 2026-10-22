"""Post-trial byte/provenance and process audit; no signals or external writes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
from verify_vision_13_4 import source_snapshot, file_digest
from verify_all_13_4 import audit_installed_paths

base = Path(os.environ['CH13_EGL_EVIDENCE'])
root = base/'legacy-clock-final'
frozen = json.loads((root/'frozen-source.json').read_text())
assert source_snapshot(Path.cwd())['files'] == frozen['snapshot']['files']
prefix = Path(os.environ['CH13_EGL_INSTALL'])
installed = {str(p.relative_to(prefix)): file_digest(p) for p in sorted(prefix.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
assert installed == frozen['installed']
known = {'ros2_control_node', 'gz', 'gzserver', 'locomotion_node', 'manipulation_node',
         'mission_commander', 'state_manager', 'vision_processor', 'object_detector',
         'robot_state_publisher', 'tracking_requester'}
residuals = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        argv = (proc/'cmdline').read_bytes().decode(errors='replace').split('\0')
        state = (proc/'stat').read_text().split(') ', 1)[1].split()[0]
        if argv and state != 'Z' and (Path(argv[0]).name in known
                or any('gz-sim-server' in a for a in argv)
                or (Path(argv[0]).name in ('python', 'python3') and len(argv)>1
                    and Path(argv[1]).name in known)):
            residuals.append(dict(pid=int(proc.name), state=state, argv=argv))
    except (OSError, IndexError):
        pass
assert not residuals, residuals
underlay = '/home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control'
def git(*args):
    return subprocess.run(['git', '-C', underlay, *args], check=True,
                          capture_output=True, text=True).stdout.strip()
head, dirty = git('rev-parse', 'HEAD'), git('status', '--porcelain')
assert head == 'c261f5552edf124d1000a23fb25b6c07cadeb807' and not dirty
output = dict(status='PASS', observed_at=time.time(), uid=os.getuid(),
    current_source_files=len(frozen['snapshot']['files']), installed_files=len(installed),
    installation_audit=audit_installed_paths(prefix, Path.cwd()), live_engine_runtime=residuals,
    external_underlay=dict(path=underlay, head=head, dirty=dirty),
    manifest_sha256=file_digest(root/'frozen-source.json'))
with (base/'FINAL_POST_TRIAL_AUDIT.json').open('x') as stream:
    json.dump(output, stream, indent=2)
print(json.dumps({k:v for k,v in output.items() if k != 'installation_audit'}, indent=2))
