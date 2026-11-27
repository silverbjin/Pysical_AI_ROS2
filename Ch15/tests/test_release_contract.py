import hashlib,io,json,os,sys,tarfile,tempfile,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from verify_evidence import digest,verify,valid_name
from owner_runner import pack,source,Blocked,ORDER
class ReleaseContract(unittest.TestCase):
    def test_sha_drift(self):
        with self.assertRaisesRegex(Blocked,'SOURCE_SHA_DRIFT'):source('0'*40)
    def test_archive_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)/'run';r.mkdir()
            for n in ('owner-result.json','source-receipt.json','environment.json','process_audit.json'):(r/n).write_text('{}')
            (r/'raw.mcap').write_bytes(b'mock bytes')
            a=pack(r);self.assertEqual(a['verified_files'],5)
            arc=r.parent/'run.evidence.tar.gz';side=arc.with_name(arc.name+'.sha256')
            side.write_text('0'*64+'  '+arc.name+'\n')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA_DRIFT'):verify(arc,side)
    def test_wrong_internal_and_path(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'x.tar.gz';s=Path(d)/'x.sha256'
            for name,manifest,reason in [('data','0'*64+'  data\n','INTERNAL_HASH'),('../escape','0'*64+'  data\n','UNSAFE_ARCHIVE')]:
                with tarfile.open(a,'w:gz') as t:
                    for n,b in [(name,b'x'),('manifest.sha256',manifest.encode())]:
                        m=tarfile.TarInfo(n);m.size=len(b);t.addfile(m,io.BytesIO(b))
                s.write_text(digest(a)+'  '+a.name+'\n')
                with self.assertRaisesRegex(ValueError,reason):verify(a,s)
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)/'run';r.mkdir();(r/'link').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError,'SYMLINK'):pack(r)
    def test_mapping(self):
        m=json.loads((root/'evidence/release_traceability.json').read_text())
        for key,prefix,count in [('code','C',24),('cli','CLI',7),('exercises','Q',12),('guides','15.',9)]:
            expected={prefix+(str(i) if key in ('guides','exercises') else f'{i:02d}') for i in range(1,count+1)}
            self.assertEqual(set(m[key]),expected)
            for row in m[key].values():
                for p in row['paths']:self.assertTrue((root.parent/p).is_file(),p)
        self.assertEqual(ORDER,('build','mock','physical_basic','cube','joint','faults'))
if __name__=='__main__':unittest.main()
