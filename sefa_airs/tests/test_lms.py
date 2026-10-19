import json
from urllib.parse import parse_qs
import httpx
import pytest
from lms import parse_engagement_rows, parse_grade_rows, MoodleClient, MoodleError, days_since


def test_engagement_rows_accept_never_and_reject_bad_counts():
    records, errors = parse_engagement_rows([
        {'student_no': 'A1', 'last_access': '2026-10-01', 'activities_completed': '3', 'activities_total': '10'},
        {'student_no': 'A2', 'last_access': 'Never'},
        {'student_no': 'A3', 'last_access': '2026-10-01', 'activities_completed': '11', 'activities_total': '10'},
    ])
    assert records[0]['activities_completed'] == 3 and records[1]['last_access'] is None
    assert errors == ['Row 4: activities_completed is larger than activities_total']


def test_engagement_requires_columns():
    with pytest.raises(ValueError, match='student_no,last_access'):
        parse_engagement_rows([{'id': 1}])


def test_moodle_percentage_export_skips_blanks_and_course_total():
    rows = [{'First name': 'A', 'ID number': 'S1', 'Quiz: Week 1 (Percentage)': '80.00 %',
             'Assignment: Essay (Percentage)': '-', 'Course total (Percentage)': '80.00 %'}]
    records, errors = parse_grade_rows(rows)
    assert errors == []
    assert records == [{'student_no': 'S1', 'item': 'Quiz: Week 1', 'kind': 'quiz', 'score': 80.0, 'max_score': 100.0}]


def test_generic_grade_template():
    records, errors = parse_grade_rows([{'student_no': 'S1', 'item': 'Assignment: Case', 'score': '15', 'max_score': '20'}])
    assert not errors and records[0]['kind'] == 'assignment' and records[0]['max_score'] == 20


def test_grade_export_without_percentage_columns_explains_how_to_export():
    with pytest.raises(ValueError, match='Percentage'):
        parse_grade_rows([{'ID number': 'S1', 'Quiz: Week 1 (Real)': '8'}])


def _moodle(handler):
    def respond(request):
        params = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        assert params['wstoken'] == 'secret' and params['moodlewsrestformat'] == 'json'
        return httpx.Response(200, json=handler(params))
    return MoodleClient('https://moodle.example.test/', 'secret', transport=httpx.MockTransport(respond))


def test_moodle_client_maps_users_and_grade_items():
    def handler(params):
        if params['wsfunction'] == 'core_enrol_get_enrolled_users':
            return [{'id': 7, 'idnumber': 'S1', 'username': 's1', 'lastcourseaccess': 1791763200},
                    {'id': 8, 'idnumber': '', 'username': 'teacher', 'lastcourseaccess': 0}]
        return {'usergrades': [{'userid': 7, 'gradeitems': [
            {'itemtype': 'mod', 'itemmodule': 'quiz', 'itemname': 'Quiz 1', 'graderaw': 7, 'grademax': 10},
            {'itemtype': 'mod', 'itemmodule': 'assign', 'itemname': 'Essay', 'graderaw': None, 'grademax': 20},
            {'itemtype': 'course', 'itemname': None, 'graderaw': 7, 'grademax': 10}]}]}
    engagement, grades = _moodle(handler).course_evidence(5)
    assert engagement[0]['keys'] == ['S1', 's1'] and engagement[0]['last_access'] == '2026-10-12'
    assert engagement[1]['last_access'] is None
    assert grades == [{'keys': ['S1', 's1'], 'item': 'Quiz 1', 'kind': 'quiz', 'score': 7.0, 'max_score': 10.0}]


def test_moodle_errors_are_reported():
    client = _moodle(lambda params: {'exception': 'webservice_access_exception', 'message': 'Access control exception'})
    with pytest.raises(MoodleError, match='Access control'):
        client.course_evidence(5)
    with pytest.raises(MoodleError, match='not configured'):
        MoodleClient('', '')


def test_days_since():
    from datetime import date
    assert days_since('2026-10-01', date(2026, 10, 19)) == 18 and days_since(None) is None
