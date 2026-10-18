"""Deterministic, privacy-conscious module delivery monitoring.

Missing registers are NOT student absences. Expected coverage is a pacing
indicator, not a substitute for verified syllabus-topic delivery.
"""
from collections import Counter, defaultdict
from datetime import date
from modular_calendar import generate_calendar


def monitor(calendar, enrolled_student_ids, attendance_records, coverage_rows, as_of=None, target=85.0):
    today = date.fromisoformat(as_of) if isinstance(as_of, str) else (as_of or date.today())
    expected = [r for r in calendar['days'] if r['activity'] == 'teaching' and date.fromisoformat(r['date']) <= today]
    expected_dates = {r['date'] for r in expected}
    enrolments = set(enrolled_student_ids)
    by_day = defaultdict(dict)
    for record in attendance_records:
        day = record['session_date']
        student = record['student_id']
        if day in expected_dates and student in enrolments:
            by_day[day][student] = record['status']
    weekly = defaultdict(lambda: {'scheduled_days': 0, 'complete_register_days': 0, 'recorded': 0,
                                  'expected_records': 0, 'present': 0, 'late': 0, 'absent': 0})
    daily = []
    for item in expected:
        d = item['date']; w = date.fromisoformat(d).isocalendar()
        week = f'{w.year}-W{w.week:02d}'
        counts = Counter(by_day[d].values())
        recorded = sum(counts.values())
        complete = bool(enrolments) and recorded == len(enrolments)
        daily.append({'date': d, 'week': week, 'day_number': item['day_number'],
                      'expected_students': len(enrolments), 'recorded_students': recorded,
                      'missing_students': len(enrolments) - recorded,
                      'register_complete': complete, 'present': counts['present'],
                      'late': counts['late'], 'absent': counts['absent']})
        bucket = weekly[week]
        bucket['scheduled_days'] += 1
        bucket['complete_register_days'] += int(complete)
        bucket['recorded'] += recorded
        bucket['expected_records'] += len(enrolments)
        for status in ('present', 'late', 'absent'):
            bucket[status] += counts[status]
    planned = sum(float(r['planned_hours']) for r in coverage_rows)
    delivered = sum(min(max(0, float(r['delivered_hours'])), float(r['planned_hours'])) for r in coverage_rows)
    actual = round(100 * delivered / planned, 1) if planned > 0 else None
    scheduled_fraction = len(expected) / calendar['teaching_days'] if calendar['teaching_days'] else 0
    pace = round(100 * scheduled_fraction, 1)
    recorded = sum(d['recorded_students'] for d in daily)
    expected_records = sum(d['expected_students'] for d in daily)
    attended = sum(d['present'] + d['late'] for d in daily)
    completeness = round(100 * recorded / expected_records, 1) if expected_records else None
    observed_rate = round(100 * attended / recorded, 1) if recorded else None
    alerts = []
    missing = [d['date'] for d in daily if not d['register_complete']]
    if missing:
        alerts.append({'type': 'incomplete_attendance', 'severity': 'warning',
                       'message': f'{len(missing)} scheduled teaching day(s) have incomplete attendance registers',
                       'dates': missing})
    if actual is None:
        alerts.append({'type': 'no_coverage_plan', 'severity': 'info',
                       'message': 'No weekly coverage plan has been uploaded'})
    elif actual + 0.01 < target * scheduled_fraction:
        alerts.append({'type': 'coverage_behind', 'severity': 'warning',
                       'message': f'Recorded coverage {actual}% is below indicative pacing threshold {round(target * scheduled_fraction, 1)}%'})
    if completeness is not None and completeness < 90:
        alerts.append({'type': 'low_register_completeness', 'severity': 'warning',
                       'message': f'Attendance record completeness is {completeness}%'})
    return {'as_of': today.isoformat(), 'scheduled_teaching_days_elapsed': len(expected),
            'total_teaching_days': calendar['teaching_days'], 'calendar_pace_percent': pace,
            'coverage_percent': actual, 'coverage_target_percent': target,
            'indicative_coverage_pace_percent': round(target * scheduled_fraction, 1),
            'attendance_record_completeness_percent': completeness,
            'attendance_rate_among_recorded_percent': observed_rate,
            'attendance_denominator': recorded, 'expected_attendance_records': expected_records,
            'daily': daily, 'weekly': [{'week': k, **v} for k, v in sorted(weekly.items())],
            'alerts': alerts,
            'caveat': 'Incomplete registers are not counted as absences. Coverage is based on reported delivered topic hours; schedule pace is indicative only.'}
