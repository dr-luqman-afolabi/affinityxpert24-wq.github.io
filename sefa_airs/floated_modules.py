"""2023-only approved curriculum catalogue and course float validation.

No course may be offered unless its code exists in the approved 2023 catalogue.
A float is a separately authorized teaching instance of that curriculum module.
"""
import csv
from pathlib import Path

PROGRAMMES = ('Economics', 'Finance', 'Accounting')
YEAR = '2023'


def catalogue(root: Path, programme: str):
    if programme not in PROGRAMMES:
        raise ValueError('Invalid programme')
    source = root / 'curriculum_review' / f'{programme.lower()}_2023_review.csv'
    with source.open(encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    return [dict(r, version=YEAR, approval_status='approved') for r in rows if r['version'].startswith(YEAR)]


def find_module(root: Path, programme: str, code: str):
    matches = [r for r in catalogue(root, programme) if r['module_code'].upper() == code.strip().upper()]
    return matches[0] if matches else None


def validate_float(root: Path, programme: str, code: str, title: str):
    row = find_module(root, programme, code)
    if not row:
        raise ValueError('Course is not listed in the approved 2023 curriculum for this programme')
    if row['module_title'].casefold().strip() != title.casefold().strip():
        raise ValueError(f"Title mismatch; approved curriculum title is: {row['module_title']}")
    return row
