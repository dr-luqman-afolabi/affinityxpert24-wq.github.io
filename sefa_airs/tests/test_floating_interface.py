import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FloatingInterfaceTests(unittest.TestCase):
    def test_course_selection_is_floated_dropdown(self):
        html=(ROOT/'templates/index.html').read_text()
        self.assertIn('name="code" required',html)
        self.assertIn('Select a floated module',html)
        self.assertIn('name="title" readonly required',html)
        self.assertIn('name="session_type"',html)
        self.assertIn('name="intake"',html)
    def test_floating_uses_server_catalogue(self):
        js=(ROOT/'static/floating.js').read_text()
        self.assertIn('/api/curriculum-catalogue',js)
        self.assertIn('/api/floated-modules',js)
        self.assertIn('/api/float-module',js)
    def test_only_2023_catalogues_shipped(self):
        for p in ('economics','finance','accounting'):
            self.assertTrue((ROOT/'curriculum_review'/f'{p}_2023_review.csv').exists())
        self.assertFalse(any((ROOT/'curriculum_review').glob('*2017*')))
if __name__=='__main__':unittest.main()
