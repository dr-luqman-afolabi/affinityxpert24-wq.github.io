from modular_calendar import generate_calendar
from weekly_trends import weekly_trends

def test_weekly_trend_distinguishes_missing():
    cal = generate_calendar('2026-01-05', 'morning', 10)
    days = [d for d in cal['days'] if d['activity']=='teaching']
    data = weekly_trends(cal, [{'week_no':1,'planned_hours':6,'delivered_hours':3}],
                         [{'session_date':days[0]['date'],'student_id':1,'status':'present'}],
                         [1,2],as_of=days[0]['date'])
    assert data[0]['topic_coverage_percent']==50
    assert data[0]['register_completeness_percent']==50
    assert data[0]['observed_attendance_percent']==100

def test_no_coverage_plan_not_zero():
    cal=generate_calendar('2026-01-05','evening',15)
    data=weekly_trends(cal,[],[],[1],as_of='2026-01-06')
    assert data[0]['topic_coverage_percent'] is None
    assert data[0]['observed_attendance_percent'] is None
