import hashlib,importlib.util,json,pathlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('assets',ROOT/'scripts/prepare_native_assets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(raw,expected,path):
    return dict(path=path,upstream_git_size=len(raw),upstream_git_blob=m.blob(raw),locked_size=len(expected),locked_sha256=m.digest(expected))
class RecoveryTests(unittest.TestCase):
    def test_exact_raw_binary(self):
        b=b'\x00\xff\n';self.assertEqual(m.select(b,row(b,b,'a.pt')),(b,'EXACT_RAW'))
    def test_exact_text_conversion(self):
        b=b'a\nb\n';c=b'a\r\nb\r\n';self.assertEqual(m.select(b,row(b,c,'a.obj')),(c,'LF_TO_CRLF_EXACT_HASH'))
    def test_no_binary_conversion(self):
        b=b'a\n'
        with self.assertRaisesRegex(ValueError,'NON_TEXT_DRIFT'):m.select(b,row(b,b'a\r\n','a.pt'))
    def test_wrong_git_blob(self):
        b=b'a\n'
        with self.assertRaisesRegex(ValueError,'UPSTREAM_BLOB_DRIFT'):m.select(b'c\n',row(b,b,'a.py'))
    def test_no_approximate_conversion(self):
        b=b'a\n'
        with self.assertRaisesRegex(ValueError,'CRLF_CANDIDATE_MISMATCH'):m.select(b,row(b,b'b\r\n','a.py'))
    def test_no_mixed_eol(self):
        b=b'a\r\nb\n'
        with self.assertRaisesRegex(ValueError,'NOT_PURE_LF_TEXT'):m.select(b,row(b,b'a\r\nb\r\n','a.py'))
    def test_contract_fields(self):
        c=json.loads((ROOT/'dependencies/ch13_contract.lock.json').read_text())
        self.assertEqual(c['source_sha'],c['base_sha']);self.assertEqual(c['basic_checks'],c['assessor_keys']);self.assertEqual(len(c['assessor_keys']),10)
        self.assertTrue(all(x.startswith('Ch13/') for x in c['source_blobs']))
if __name__=='__main__':unittest.main()
