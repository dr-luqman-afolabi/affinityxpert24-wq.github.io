"""Flexible modular academic calendar; academic credits are not clock hours."""
from dataclasses import dataclass
from datetime import date, timedelta

TIMETABLE = {
    ('morning', 10): ('08:30', '11:30'), ('morning', 15): ('08:30', '12:00'),
    ('evening', 10): ('18:00', '21:00'), ('evening', 15): ('18:00', '21:00'),
    ('weekend', 10): ('08:30', '14:00'), ('weekend', 15): ('08:30', '16:00'),
}

@dataclass(frozen=True)
class SessionRule:
    start: str
    end: str
    teaching_days: int
    cat_day: int
    exam_day: int
    gross_hours_per_day: float

def _minutes(value):
    try:
        h, m = map(int, value.split(':'))
        if not 0 <= h <= 23 or not 0 <= m <= 59:
            raise ValueError()
        return h * 60 + m
    except (AttributeError, ValueError):
        raise ValueError('Time must be HH:MM in 24-hour format')

def build_rule(session, credits, before_cat=10, after_cat=5, evening_extra_days=1,
               start_time=None, end_time=None, extra_days_before_cat=None):
    if (session, credits) not in TIMETABLE:
        raise ValueError('Unsupported session or credit value')
    if any(type(v) is not int or v < 0 for v in (before_cat, after_cat, evening_extra_days)) or before_cat < 1:
        raise ValueError('Invalid teaching day configuration')
    extra = evening_extra_days if session == 'evening' else 0
    if extra_days_before_cat is not None:
        if type(extra_days_before_cat) is not int or not 0 <= extra_days_before_cat <= extra:
            raise ValueError('Invalid placement of extra teaching days')
        before_extra = extra_days_before_cat
    else:
        before_extra = extra
    start, end = TIMETABLE[(session, credits)]
    start, end = start_time or start, end_time or end
    duration = _minutes(end) - _minutes(start)
    if duration <= 0:
        raise ValueError('End time must be later than start time')
    before = before_cat + before_extra
    total_teaching = before_cat + after_cat + extra
    return SessionRule(start, end, total_teaching, before + 1, total_teaching + 2, duration / 60)

def generate_calendar(start_date, session, credits, weekdays=None, break_minutes=0,
                      before_cat=10, after_cat=5, evening_extra_days=1,
                      start_time=None, end_time=None, extra_days_before_cat=None,
                      excluded_dates=None, coverage_target=85, max_calendar_days=366):
    """Produce planned sessions only; holidays are skipped, never silently counted as teaching."""
    rule = build_rule(session, credits, before_cat, after_cat, evening_extra_days,
                      start_time, end_time, extra_days_before_cat)
    if weekdays is None:
        weekdays = [5, 6] if session == 'weekend' else [0, 1, 2, 3, 4]
    if not weekdays or any(type(x) is not int or x not in range(7) for x in weekdays):
        raise ValueError('Weekdays must be integers 0–6')
    if type(break_minutes) is not int or not 0 <= break_minutes < rule.gross_hours_per_day * 60:
        raise ValueError('Invalid break duration')
    if not isinstance(coverage_target, (int, float)) or not 0 <= coverage_target <= 100:
        raise ValueError('Coverage target must be 0–100')
    if type(max_calendar_days) is not int or not 1 <= max_calendar_days <= 3660:
        raise ValueError('Invalid calendar horizon')
    cursor = date.fromisoformat(start_date)
    excluded = {date.fromisoformat(x) for x in (excluded_dates or [])}
    rows = []
    first_post_cat = rule.cat_day + 1
    for _ in range(max_calendar_days):
        if len(rows) >= rule.exam_day:
            break
        if cursor.weekday() in weekdays and cursor not in excluded:
            n = len(rows) + 1
            kind = 'cat' if n == rule.cat_day else 'exam' if n == rule.exam_day else 'teaching'
            rows.append({'day_number': n, 'date': cursor.isoformat(), 'activity': kind,
                         'phase': 'assessment' if kind != 'teaching' else ('post_cat' if n >= first_post_cat else 'pre_cat'),
                         'start': rule.start, 'end': rule.end,
                         'planned_teaching_hours': round(rule.gross_hours_per_day - break_minutes / 60, 2) if kind == 'teaching' else 0})
        cursor += timedelta(days=1)
    if len(rows) < rule.exam_day:
        raise ValueError('Insufficient eligible days within calendar horizon')
    return {'session': session, 'credits': credits, 'teaching_days': rule.teaching_days,
            'total_scheduled_days': rule.exam_day, 'cat_day_number': rule.cat_day,
            'gross_contact_hours': round(rule.teaching_days * rule.gross_hours_per_day, 2),
            'planned_teaching_hours': round(sum(r['planned_teaching_hours'] for r in rows), 2),
            'coverage_target_percent': coverage_target,
            'planned_hours_at_target': round(sum(r['planned_teaching_hours'] for r in rows) * coverage_target / 100, 2),
            'calendar_end_date': rows[-1]['date'], 'days': rows,
            'note': 'Planned timetable only; actual coverage requires verified delivery records. CAT and exam excluded from teaching hours.'}
