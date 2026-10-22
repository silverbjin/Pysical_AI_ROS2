"""Library ownership audit against an actual child process, not an engine substitute."""
from pathlib import Path
import subprocess
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_vision_13_4 as runner


def test_owned_mapping_rejects_unloaded_library_and_records_actual_child(tmp_path):
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)'],start_new_session=True)
    try:
        maps=Path(f'/proc/{child.pid}/maps')
        end=time.monotonic()+1
        lines=[]
        while time.monotonic()<end:
            lines=[line for line in maps.read_text().splitlines() if '/libc.so' in line]
            if lines:
                break
            time.sleep(.005)
        assert lines
        expected=Path(lines[0].split()[-1]).resolve()
        audit=runner.mapped_owned_library(child,expected)
        assert audit['pid']==child.pid and audit['pgid']==child.pid
        assert audit['library_path']==str(expected) and len(audit['library_sha256'])==64
        unloaded=tmp_path/'not-loaded.so'
        unloaded.write_bytes(b'not an installed or mapped plugin')
        with pytest.raises(RuntimeError,match='not mapped'):
            runner.mapped_owned_library(child,unloaded)
    finally:
        child.wait(timeout=3)
