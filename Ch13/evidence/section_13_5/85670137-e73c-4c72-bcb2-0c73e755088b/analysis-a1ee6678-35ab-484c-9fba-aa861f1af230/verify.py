"""Verify offline artifacts and current process inventory; no engine operations."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

here = Path(__file__).resolve().parent
repo = next(p for p in here.parents if (p/'Ch13/ros2_ws/src').is_dir())
result = (here/'result.json').read_bytes()
assert result == (here/'result-repeat.json').read_bytes()
parsed = json.loads(result)
assert parsed['runtime_manifest_file_count'] == 119 and not parsed['runtime_mismatches']
assert hashlib.sha256((here/'analyze.py').read_bytes()).hexdigest() == parsed['analysis_source_sha256']
arm = json.loads((here/'arm-hold.json').read_text())
assert hashlib.sha256((here/'arm_hold.py').read_bytes()).hexdigest() == arm['script_sha256']
assert hashlib.sha256(result).hexdigest() == arm['reference_analysis_sha256']
assert parsed['conclusions']['section_completed'] is False
assert parsed['original_status'] == 'FAIL'
doc = repo/'Ch13/docs/SECTION_13_5_MUJOCO_NATIVE_CAUSE_ANALYSIS_KO.md'
text = doc.read_text()
links = re.findall(r'\]\(([^)]+)\)', text)
for target in links:
    assert not target.startswith(('http:', 'https:'))
    assert (doc.parent/target).is_file(), target
assert text.count('```') == 2 and text.count('```mermaid') == 1
assert hashlib.sha256(result).hexdigest() in text
assert (repo/'Ch13/docs/SECTION_13_4_DEBUGGING_LESSONS_KO.md').stat().st_size == 40723
processes = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        args = (proc/'cmdline').read_bytes().decode(errors='replace').split('\0')
        names = {Path(a).name for a in args[:2] if a}
        if names.intersection({'ros2_control_node', 'crawl_controller', 'motion_guard',
                               'probe_navigation_13_5.py', 'carry_manager', 'navigation_startup'}) or (
                'gz' in names and 'sim' in names):
            processes.append(dict(pid=int(proc.name), first_args=args[:2]))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
assert not processes, processes
head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
branch = subprocess.check_output(['git', '-C', str(repo), 'branch', '--show-current'], text=True).strip()
out = dict(scope='offline_verification_only_not_engine_acceptance', uid=os.getuid(),
    head=head, branch=branch, duplicate_analysis_byte_identical=True,
    result_sha256=hashlib.sha256(result).hexdigest(), runtime_files_unchanged=119,
    source_self_checks='inverse quintic; independent general FK parity; perturbation sensitivity',
    arm_and_gripper_goals_constant_in_selected_snapshots=True,
    local_document_links_checked=len(links), mermaid_fence_checked=True,
    mermaid_render_test_performed=False,
    matching_runtime_processes=processes, new_engine_trials=0,
    original_failure_preserved=True, commit_or_push_performed=False,
    artifact_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(here.iterdir()) if p.is_file() and p.name!='verification.json'})
with (here/'verification.json').open('x') as file:
    json.dump(out, file, indent=2, ensure_ascii=False, allow_nan=False)
    file.write('\n')
print(json.dumps(out, ensure_ascii=False))
