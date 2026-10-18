from import_preview import attendance_rows,profile_rows

def test_valid_attendance():
    data,errors=attendance_rows([{'student_no':'S1','session_date':'2026-10-19','status':'Present'}],{'S1':1})
    assert not errors and data[0]['status']=='present'

def test_invalid_attendance_is_blocked():
    data,errors=attendance_rows([{'student_no':'S2','session_date':'2026-10-19','status':'present'}],{'S1':1})
    assert errors and not data

def test_duplicate_attendance_blocked():
    row={'student_no':'S1','session_date':'2026-10-19','status':'present'}
    data,errors=attendance_rows([row,row],{'S1':1})
    assert errors

def test_conflicting_profile_blocked():
    def validator(rows,programme):return rows
    rows=[{'student_no':'S1','name':'Alice','programme':'Finance','email':'new@example.com','phone':'','intake':'','session':''}]
    _,errors=profile_rows(rows,'Finance',{'S1':{'name':'Alice','programme':'Finance','email':'old@example.com'}},validator)
    assert errors
