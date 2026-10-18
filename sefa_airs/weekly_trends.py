"""Weekly module monitoring; missing delivery data is never interpreted as zero teaching."""
from collections import defaultdict
from datetime import date


def weekly_trends(calendar, coverage_rows, attendance_rows, student_ids, as_of=None):
    cutoff = date.fromisoformat(as_of) if isinstance(as_of, str) else (as_of or date.today())
    teaching = [d for d in calendar['days'] if d['activity'] == 'teaching' and date.fromisoformat(d['date']) <= cutoff]
    buckets = defaultdict(lambda: {'teaching_days': 0, 'planned_calendar_hours': 0.0, 'expected_register_entries': 0,
                                   'recorded_register_entries': 0, 'present_or_late': 0, 'topic_planned_hours': 0.0,
                                   'topic_delivered_hours': 0.0, 'topics': 0})
    by_date = {}
    for d in teaching:
        dt = date.fromisoformat(d['date']); week = f'{dt.isocalendar().year}-W{dt.isocalendar().week:02d}'
        by_date[d['date']] = week
        b = buckets[week]; b['teaching_days'] += 1
        b['planned_calendar_hours'] += d['planned_teaching_hours']
        b['expected_register_entries'] += len(student_ids)
    valid_students = set(student_ids)
    unique = {}
    for a in attendance_rows:
        if a['session_date'] in by_date and a['student_id'] in valid_students:
            unique[(a['session_date'], a['student_id'])] = a['status']
    for (day, _student), status in unique.items():
        b = buckets[by_date[day]]; b['recorded_register_entries'] += 1
        b['present_or_late'] += int(status in ('present', 'late'))
    for row in coverage_rows:
        week_no = row.get('week_no')
        # week_no is a teaching-plan ordinal, not an ISO week: map through ordered calendar weeks.
        ordered_weeks = sorted(buckets)
        if not isinstance(week_no, int) or week_no < 1 or week_no > len(ordered_weeks):
            continue
        b = buckets[ordered_weeks[week_no - 1]]
        planned = max(0.0, float(row['planned_hours']))
        delivered = min(planned, max(0.0, float(row['delivered_hours'])))
        b['topic_planned_hours'] += planned; b['topic_delivered_hours'] += delivered; b['topics'] += 1
    output = []
    for week, b in sorted(buckets.items()):
        expected = b['expected_register_entries']; recorded = b['recorded_register_entries']
        planned = b['topic_planned_hours']
        output.append({'week': week, **{k: round(v, 2) if isinstance(v, float) else v for k,v in b.items()},
                       'register_completeness_percent': round(100*recorded/expected, 1) if expected else None,
                       'observed_attendance_percent': round(100*b['present_or_late']/recorded, 1) if recorded else None,
                       'topic_coverage_percent': round(100*b['topic_delivered_hours']/planned, 1) if planned else None})
    return output
