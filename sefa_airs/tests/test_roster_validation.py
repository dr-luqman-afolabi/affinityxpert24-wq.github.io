from app import validate_roster_rows
import pytest

def test_optional_profiles():
    records=validate_roster_rows([{'student_no':'A1','name':'Example','programme':'Finance','email':'a@example.test','session':'Evening'}],'Finance')
    assert records[0]['session']=='evening'

def test_duplicate_rejected():
    with pytest.raises(ValueError,match='duplicate'):
        validate_roster_rows([{'student_no':'A','name':'A','programme':'Finance'},{'student_no':'A','name':'A','programme':'Finance'}],'Finance')

def test_programme_mismatch_rejected():
    with pytest.raises(ValueError,match='programme mismatch'):
        validate_roster_rows([{'student_no':'A','name':'A','programme':'Accounting'}],'Finance')
