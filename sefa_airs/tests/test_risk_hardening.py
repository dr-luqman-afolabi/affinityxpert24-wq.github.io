from risk_intelligence import analyze_student

def test_assessment_uses_points_not_equal_percentages():
    result=analyze_student([], [{'score':9,'max_score':10},{'score':0,'max_score':90}])
    assert result['assessment_percent']==9.0

def test_calendar_excludes_non_teaching_days_and_duplicate_registers():
    records=[{'date':'2026-10-01','status':'absent'}, {'date':'2026-10-01','status':'absent'},
             {'date':'2026-10-02','status':'absent'}, {'date':'2026-10-03','status':'present'}]
    result=analyze_student(records,[],scheduled_dates=['2026-10-01','2026-10-03'])
    assert result['recorded_sessions']==2 and result['recorded_absences']==1
    assert result['excluded_attendance_entries']==2

def test_empty_scheduled_calendar_never_counts_absences():
    result=analyze_student([{'date':'2026-10-01','status':'absent'}],[],scheduled_dates=[])
    assert result['recorded_sessions']==0 and result['risk_band']=='insufficient data'
