import importlib.util
import shutil
from pathlib import Path
import pytest


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def test_published_archive_restores_hash_checked_evidence_without_models(tmp_path):
    root=Path(__file__).resolve().parents[5]
    archive=load('archive_bt_test',root/'Ch13/scripts/reuse_13_7/archive_evidence.py')
    restore=load('restore_bt_test',root/'Ch13/scripts/reuse_13_6/restore_evidence.py')
    archive.ROOT=tmp_path
    folder=tmp_path/'Ch13/evidence/section_13_7_bt/case';folder.mkdir(parents=True)
    (folder/'proof.json').write_text('{"result":"PASS"}')
    (folder/'robot.urdf').write_text('excluded model')
    (folder/'planner.yaml').write_text('embedded model excluded')
    archive.archive(folder)
    destination=tmp_path/'download';destination.mkdir()
    for name in ('raw.tar.gz','raw_manifest.json'):shutil.copy2(folder/name,destination/name)
    result=restore.restore(destination)
    assert result['result']=='PASS' and result['restored']==1
    assert (destination/'proof.json').read_text()=='{"result":"PASS"}'
    assert not (destination/'robot.urdf').exists() and not (destination/'planner.yaml').exists()
    with pytest.raises(ValueError):archive.archive(folder)
