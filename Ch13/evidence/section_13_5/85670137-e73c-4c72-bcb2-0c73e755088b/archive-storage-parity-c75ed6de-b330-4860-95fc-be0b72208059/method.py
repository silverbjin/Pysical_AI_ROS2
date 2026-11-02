"""Compare new storage inventory to the ALREADY verified real failed archive."""
import hashlib,json,tempfile,uuid
from pathlib import Path
from archive_native_storage import export_closed,archive_sources
repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
name='native-g2-mujoco-095dc500-a35b-48c5-b81c-cef60e90f964';original=native/name
old=base/'task8-preflight-pair-g2-mujoco-095dc500-a35b-48c5-b81c-cef60e90f964.json'
old_ledger=json.loads(old.read_text());assert old_ledger['status']=='FAIL'
out=base/('archive-storage-parity-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'storage-method.py').write_bytes(Path(__file__).with_name('archive_native_storage.py').read_bytes())
with tempfile.TemporaryDirectory(prefix='ch13-archive-parity-') as temporary:
    destination=Path(temporary)/name
    ledger=export_closed(original,destination,native,archive_large=True)
    (destination/'storage-copy-ledger.json').write_text(json.dumps(ledger))
    records=archive_sources(destination,native);compared=[]
    for path,relative,expected in records:
        if relative=='storage-copy-ledger.json':continue # New storage provenance only.
        prior=old_ledger['members']['evidence/'+name+'/'+relative]
        assert expected==prior['sha256'] and path.stat().st_size==prior['size']
        compared.append(dict(path=relative,size=prior['size'],sha256=expected))
    assert json.loads((destination/'result.json').read_text())['status']=='FAIL'
    report=dict(scope='post_reap_storage_inventory_parity_not_new_engine_or_result_promotion',
        prior_trial=name,prior_archive_sha256=old_ledger['sha256'],
        prior_archive_ledger_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
        compared_native_files=len(compared),compared_bytes=sum(r['size'] for r in compared),
        omitted_duplicate_files=ledger['not_duplicated'],all_original_bytes_match=True,
        original_files_deleted=False,original_verdict_unchanged='FAIL',files=compared)
(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in dict(output=str(out),**report).items() if k not in ('files','omitted_duplicate_files')},indent=2))
