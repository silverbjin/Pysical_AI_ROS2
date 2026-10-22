import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
root = Path(os.environ['CH13_EGL_EVIDENCE'])
testroot = ET.parse(root/'task6-final-pytest.xml').getroot()
suites = [testroot] if testroot.tag == 'testsuite' else list(testroot)
assert sum(int(v.attrib['tests']) for v in suites) == 345
assert all(int(v.attrib.get(k,0)) == 0 for v in suites for k in ('errors','failures','skipped'))
assert re.search(r'Summary: 182 tests, 0 errors, 0 failures, 0 skipped', (root/'task6-final-result.log').read_text())
audit = subprocess.run([sys.executable,'Ch13/scripts/verify_all_13_4.py','--audit-install-prefix',
                        os.environ['CH13_EGL_INSTALL']],text=True,capture_output=True,check=True)
assert len(json.loads(audit.stdout)) == 5
subprocess.run([sys.executable,'.superpowers/sdd/2026-10-20-egl-camera-latency-plan/task5-audit.py'],check=True)
checked = 0
for name in ('LAB_13_4_GUIDE_KO.md','SECTION_13_4_REPORT_KO.md','SECTION_13_4_REVIEW_KO.md',
             'SECTION_13_4_ROOT_CAUSE_ANALYSIS_KO.md','SECTION_13_4_EGL_TRACE_RESULTS_KO.md','REUSE_MANIFEST.md'):
    path = Path('Ch13/docs')/name
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if '://' in target or target.startswith(('#','mailto:')):
            continue
        target = target.split('#',1)[0]
        assert (path.parent/target).exists(), (name,target)
        checked += 1
changed = subprocess.check_output(['git','diff','--name-only','0ff4063..HEAD'],text=True).splitlines()
assert changed and all(v.startswith('Ch13/') for v in changed)
if '--remote' in sys.argv:
    local = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    remote = subprocess.check_output(['git','ls-remote','origin','refs/heads/feat/ch13-section-13-4'],text=True).split()[0]
    assert local == remote
    print('remote_sha_verified='+local)
print(json.dumps(dict(final_verification='PASS',source_tests=345,package_tests=182,
    installed_packages=5,local_links=checked,product_acceptance='FAIL',section13_5='HELD')))
