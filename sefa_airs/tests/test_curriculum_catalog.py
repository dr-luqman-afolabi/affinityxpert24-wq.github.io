from pathlib import Path
import csv

def test_review_catalogues():
    root=Path(__file__).resolve().parents[1]/'curriculum_review'
    for name,minimum in [('finance_2023_review.csv',30),('accounting_2023_review.csv',30),('economics_2023_review.csv',15)]:
        with (root/name).open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
        assert len(rows)>=minimum
        assert len({r['module_code'] for r in rows})==len(rows)
        assert all(r['review_status']=='needs_review' and not r['credits'] for r in rows)
