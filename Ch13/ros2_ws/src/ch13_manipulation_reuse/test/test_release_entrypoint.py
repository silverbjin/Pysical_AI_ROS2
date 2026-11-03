"""No engine or install access: missing freeze must fail before any helper."""
import os,subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[5]


@pytest.mark.parametrize('protected',['/home/jinho/ch13_reuse_r2_build','/home/jinho/ch13_reuse_r5_build'])
def test_build_guard_rejects_protected_underlay_descendants_without_mutation(tmp_path,protected):
    # Execute only the real read-only preamble, stopping before its first mkdir.
    # The protected directory and its children are never created or changed.
    source=(ROOT/'Ch13/scripts/reuse_13_6/build.sh').read_text()
    preamble=source.split('mkdir -p "$reuse_build"',1)[0]
    script=tmp_path/'guard.sh';script.write_text(preamble)
    environment=os.environ.copy();environment['CH13_REUSE_BUILD']=protected+'/must_not_be_created'
    result=subprocess.run(['bash',str(script)],env=environment,capture_output=True,text=True)
    assert result.returncode==2,'protected build descendant was admitted'


@pytest.mark.parametrize('override',[False,True])
def test_missing_source_freeze_rejects_before_install_or_engine(tmp_path,override):
    scripts=tmp_path/'Ch13/scripts/reuse_13_6';scripts.mkdir(parents=True)
    entry=scripts/'run_case.sh';entry.write_bytes((ROOT/'Ch13/scripts/reuse_13_6/run_case.sh').read_bytes())
    helper_log=tmp_path/'helpers_started'
    (scripts/'env.sh').write_text('#!/usr/bin/env bash\nprintf called >> "'+str(helper_log)+'"\nexit 0\n')
    environment=os.environ.copy();environment.pop('CH13_REUSE_FREEZE',None)
    if override:environment['CH13_REUSE_FREEZE']=str(tmp_path/'absent.json')
    result=subprocess.run(['bash',str(entry),'hold',str(tmp_path/'case')],env=environment,capture_output=True,text=True)
    assert result.returncode!=0,'missing source freeze was bypassed'
    assert not helper_log.exists(),'install or engine helper started before source admission'
