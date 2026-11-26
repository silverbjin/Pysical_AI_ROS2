import unittest
from validate_dependency_graph import audit
from pip._vendor.packaging.markers import default_environment

ENV = {**default_environment(), 'python_version': '3.12', 'python_full_version': '3.12.3'}
# Versions and requirement taken from run 45739828134 pip check / dpkg evidence.
SYSTEM = [{'name':'setuptools','version':'68.1.2'},
          {'name':'colcon-core','version':'0.21.3','requires_dist':['setuptools<80,>=30.3.0']}]

class GraphTests(unittest.TestCase):
    def test_original_conflict(self):
        r = audit(SYSTEM, [{'name':'setuptools','version':'84.2.1'}], ENV)
        self.assertEqual(r['status'], 'FAIL')
        self.assertIn('found 84.2.1', r['errors'][0])

    def test_inherited_setuptools(self):
        r = audit(SYSTEM, [{'name':'torch','version':'2.5.1+cpu','requires_dist':['setuptools; python_version >= "3.12"']}], ENV)
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['effective']['setuptools']['version'], '68.1.2')

    def test_missing_transitive_extra(self):
        rows = [{'name':'a','version':'1','requires_dist':['b[feature]']},
                {'name':'b','version':'1','requires_dist':['c; extra == "feature"']}]
        self.assertEqual(audit([], rows, ENV)['status'], 'FAIL')

    def test_inactive_marker(self):
        self.assertEqual(audit([], [{'name':'a','version':'1','requires_dist':['missing; python_version < "3.12"']}], ENV)['status'], 'PASS')

    def test_python_version(self):
        self.assertEqual(audit([], [{'name':'a','version':'1','requires_python':'>=3.13'}], ENV)['status'], 'FAIL')

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            audit([], [{'name':'a_b','version':'1'},{'name':'a-b','version':'2'}], ENV)

if __name__ == '__main__':
    unittest.main(verbosity=2)
