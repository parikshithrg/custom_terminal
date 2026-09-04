"""Explicit isolated native regression command; not imported by root discovery."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.r9n_adversarial import ROOT, exercise, fixture, run


class NativeRegression(unittest.TestCase):
    observations = []

    def test_recorded_matrix(self):
        actual = run()
        expected = json.loads((ROOT/'docs/investigations/r9n/results_v1.json').read_text())
        self.assertEqual(actual, expected)

    def check_shared(self, kind, **limits):
        with tempfile.TemporaryDirectory(prefix='synthetic_regression_', dir=ROOT/'artifacts/r9n_evaluation') as folder:
            path=fixture(Path(folder),1024)
            result=exercise(path, operations=('catalog','catalog'), **limits)
            self.observations.append({'name':kind, 'hypothesis':'Controls remain cumulative across statements',
                                      'expected_published_rows':70 if not limits else 0,
                                      'observed':result, 'evidence_type':'NATIVE_SQLITE'})
            return result

    def test_shared_success(self):
        r=self.check_shared('shared_success')
        self.assertEqual(r['published_rows'],70)
        self.assertGreater(r['reserved'],25716)

    def test_shared_rows(self):
        r=self.check_shared('shared_rows',rows=40)
        self.assertEqual(r['failed'],'ROW_LIMIT')
        self.assertEqual(r['row_seen'],41)
        self.assertEqual(r['published_rows'],0)

    def test_shared_output(self):
        r=self.check_shared('shared_output',output=11000)
        self.assertEqual(r['failed'],'OUTPUT_LIMIT')
        self.assertGreater(r['row_seen'],35)
        self.assertEqual(r['published_rows'],0)
        self.assertLessEqual(r['buffered_bytes_peak'],11000)

    @classmethod
    def tearDownClass(cls):
        print(json.dumps(cls.observations,separators=(',',':')))


if __name__=='__main__': unittest.main()
