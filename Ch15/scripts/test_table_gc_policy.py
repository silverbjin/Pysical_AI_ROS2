import gc,unittest
from table_gc_policy import defer_full_collection
class TestPolicy(unittest.TestCase):
    def test_preserve_young_and_restore(self):
        old=gc.get_threshold();r={}
        with defer_full_collection(r):
            self.assertEqual(gc.get_threshold(),(*old[:2],1_000_000))
            self.assertTrue(gc.isenabled())
            gc.collect(0);gc.collect(1)
        self.assertEqual(gc.get_threshold(),old)
        self.assertTrue(r['restored'])
        self.assertGreaterEqual(r['collections'][0],1)
        self.assertGreaterEqual(r['collections'][1],1)
        self.assertEqual(r['collections'][2],0)
    def test_exception_restores(self):
        old=gc.get_threshold();r={}
        with self.assertRaisesRegex(ValueError,'example'):
            with defer_full_collection(r):raise ValueError('example')
        self.assertEqual(gc.get_threshold(),old)
        self.assertTrue(r['restored'])
if __name__=='__main__':unittest.main()
