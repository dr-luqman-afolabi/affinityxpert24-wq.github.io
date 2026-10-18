from pathlib import Path
import pytest
from floated_modules import catalogue, find_module, validate_float
ROOT=Path(__file__).resolve().parents[1]

def test_2023_only():
    for programme in ('Economics','Finance','Accounting'):
        rows=catalogue(ROOT,programme)
        assert rows and all(x['version']=='2023' and x['approval_status']=='approved' for x in rows)

def test_floated_course_must_be_in_curriculum():
    with pytest.raises(ValueError):
        validate_float(ROOT,'Finance','NOT_REAL','Fake Course')

def test_title_must_match_approved_curriculum():
    row=catalogue(ROOT,'Economics')[0]
    assert find_module(ROOT,'Economics',row['module_code'])
    with pytest.raises(ValueError):validate_float(ROOT,'Economics',row['module_code'],'Not the approved title')
