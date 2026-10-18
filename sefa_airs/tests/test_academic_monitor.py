from academic_monitor import monitor
from modular_calendar import generate_calendar


def test_missing_register_not_absence():
    cal = generate_calendar('2026-10-05', 'morning', 10)
    r = monitor(cal, [1, 2], [{'student_id': 1, 'session_date': '2026-10-05', 'status': 'present'}],
                [{'planned_hours': 30, 'delivered_hours': 3}], '2026-10-06')
    assert r['expected_attendance_records'] == 4
    assert r['attendance_denominator'] == 1
    assert r['attendance_rate_among_recorded_percent'] == 100
    assert r['attendance_record_completeness_percent'] == 25
    assert len(r['daily']) == 2
    assert any(a['type'] == 'incomplete_attendance' for a in r['alerts'])


def test_cat_exam_excluded():
    cal = generate_calendar('2026-10-05', 'morning', 10)
    r = monitor(cal, [1], [], [], cal['calendar_end_date'])
    assert r['scheduled_teaching_days_elapsed'] == 15
    assert len(r['daily']) == 15
    assert r['coverage_percent'] is None


def test_weekend_aggregation():
    cal = generate_calendar('2026-10-03', 'weekend', 15)
    r = monitor(cal, [1], [{'student_id': 1, 'session_date': '2026-10-03', 'status': 'late'}], [], '2026-10-04')
    assert r['weekly'][0]['scheduled_days'] == 2
    assert r['attendance_rate_among_recorded_percent'] == 100


def test_no_future_missing_alerts():
    cal = generate_calendar('2026-11-02', 'evening', 10)
    r = monitor(cal, [1], [], [], '2026-10-18')
    assert r['daily'] == []
    assert not any(a['type'] == 'incomplete_attendance' for a in r['alerts'])
