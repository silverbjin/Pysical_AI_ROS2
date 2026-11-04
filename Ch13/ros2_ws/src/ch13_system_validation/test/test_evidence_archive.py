"""Evidence compression must be lossless, immutable, and exclude generated models."""
import hashlib,json,tarfile,uuid
import importlib.util,shutil
from pathlib import Path
import pytest
from ch13_system_validation.evidence_archive import archive_case


def case_fixture(tmp_path):
    root=tmp_path/'repo';folder=root/'Ch13/evidence/section_13_8_system'/str(uuid.uuid4())
    folder.mkdir(parents=True)
    (root.parent/'ch13_reuse_engine.lock').write_bytes(b'')
    (folder/'trial.json').write_text('{"success": false}\n')
    (folder/'engine.json').write_bytes(b'original failure evidence\n')
    (folder/'model.mjb').write_bytes(b'model should stay local')
    (folder/'planner.yaml').write_text('embedded_description: local')
    return root,folder


def test_archive_restores_exact_failure_bytes_and_keeps_raw_originals(tmp_path):
    root,folder=case_fixture(tmp_path)
    original={p.name:p.read_bytes() for p in folder.iterdir()}
    result=archive_case(root,folder)
    with tarfile.open(folder/'raw.tar.gz') as archive:
        assert set(archive.getnames())=={'trial.json','engine.json'}
        assert archive.extractfile('trial.json').read()==original['trial.json']
        assert archive.extractfile('engine.json').read()==original['engine.json']
    assert all((folder/name).read_bytes()==data for name,data in original.items())
    manifest=json.loads((folder/'raw_manifest.json').read_text())
    assert manifest['archive_sha256']==hashlib.sha256((folder/'raw.tar.gz').read_bytes()).hexdigest()
    assert {r['path'] for r in manifest['files'] if not r['published']}=={'model.mjb','planner.yaml'}
    assert result['result']=='PASS'
    # Consume the archive with the already deployed 13.6 verifier/restorer.
    script=Path(__file__).resolve().parents[5]/'Ch13/scripts/reuse_13_6/restore_evidence.py'
    spec=importlib.util.spec_from_file_location('existing_evidence_restore',script)
    restorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(restorer)
    empty=tmp_path/'empty_restore';empty.mkdir()
    for name in ('raw.tar.gz','raw_manifest.json'):shutil.copyfile(folder/name,empty/name)
    assert restorer.restore(empty)['restored']==2
    assert (empty/'engine.json').read_bytes()==original['engine.json']


def test_archive_never_overwrites_old_verdict_or_archive(tmp_path):
    root,folder=case_fixture(tmp_path);archive_case(root,folder)
    before=(folder/'raw.tar.gz').read_bytes()
    with pytest.raises(ValueError,match='immutable'):archive_case(root,folder)
    assert (folder/'raw.tar.gz').read_bytes()==before


def test_archive_rejects_non_case_paths_and_symlinks(tmp_path):
    root,folder=case_fixture(tmp_path)
    with pytest.raises(ValueError):archive_case(root,folder.parent)
    outside=tmp_path/'outside.txt';outside.write_text('external')
    (folder/'linked.txt').symlink_to(outside)
    with pytest.raises(ValueError,match='symlink'):archive_case(root,folder)
    assert not (folder/'raw.tar.gz').exists()
