"""Runtime copying must preserve bytes and the original shared engine lock."""
import hashlib,json
from pathlib import Path
import pytest
from ch13_system_validation.runtime_staging import stage_runtime


def fixture(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    (root/'source.py').write_bytes(b'print("frozen")\r\n')
    assets=tmp_path/'upstream-iit-locomanipulation-d010212';assets.mkdir()
    (assets/'weights.pt').write_bytes(b'asset-reference')
    (tmp_path/'ch13_reuse_engine.lock').write_bytes(b'')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    data=dict(source={'source.py':sha(root/'source.py')},assets=[dict(path='weights.pt',sha256=sha(assets/'weights.pt'))])
    manifest=root/'freeze.json';manifest.write_text(json.dumps(data))
    return root,manifest,data


def test_native_staging_preserves_bytes_assets_and_shared_lock(tmp_path):
    root,manifest,_=fixture(tmp_path)
    result=stage_runtime(root,manifest,tmp_path/'build')
    runtime=Path(result['runtime_root'])
    assert (runtime/'source.py').read_bytes()==(root/'source.py').read_bytes()
    assert (runtime/manifest.name).read_bytes()==manifest.read_bytes()
    assert (runtime.parent/'ch13_reuse_engine.lock').resolve()==(root.parent/'ch13_reuse_engine.lock').resolve()
    assert (runtime.parent/'upstream-iit-locomanipulation-d010212').resolve()==(root.parent/'upstream-iit-locomanipulation-d010212').resolve()
    assert result['source_manifest_sha256']==hashlib.sha256(manifest.read_bytes()).hexdigest()
    # A later edit of the development tree must not mutate the running snapshot.
    (root/'source.py').write_bytes(b'new version')
    assert (runtime/'source.py').read_bytes()==b'print("frozen")\r\n'


@pytest.mark.parametrize('kind',['source','asset'])
def test_staging_refuses_changed_source_and_asset_bytes(tmp_path,kind):
    root,manifest,_=fixture(tmp_path)
    path=root/'source.py' if kind=='source' else root.parent/'upstream-iit-locomanipulation-d010212/weights.pt'
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash'):stage_runtime(root,manifest,tmp_path/'build')


@pytest.mark.parametrize('name',['../outside.txt','/etc/passwd','C:/private.txt','a\\b'])
def test_staging_rejects_manifest_path_escape(tmp_path,name):
    root,manifest,data=fixture(tmp_path);data['source']={name:'a'*64};manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='path'):stage_runtime(root,manifest,tmp_path/'build')


def test_each_runtime_snapshot_is_new_and_never_reuses_an_old_directory(tmp_path):
    root,manifest,_=fixture(tmp_path)
    first=stage_runtime(root,manifest,tmp_path/'build');second=stage_runtime(root,manifest,tmp_path/'build')
    assert first['runtime_root']!=second['runtime_root']
    assert (Path(first['runtime_root'])/'source.py').exists()
