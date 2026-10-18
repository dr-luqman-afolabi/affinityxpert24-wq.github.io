from risk_intelligence import analyze_student,aggregate_reports

def test_missing_is_not_absence():
    r=analyze_student([],[])
    assert r['risk_index'] is None and r['risk_band']=='insufficient data'
    assert r['recorded_absences']==0

def test_late_counts_as_attendance_and_limited_evidence():
    r=analyze_student([{'status':'late'},{'status':'present'}],[])
    assert r['attendance_percent']==100 and r['risk_index'] is None

def test_support_and_explanations():
    r=analyze_student([{'status':'absent'}]*4,[{'score':20,'max_score':100}],[{'status':'open'}])
    assert r['risk_band']=='critical' and r['requires_human_review']
    assert r['open_interventions']==1 and r['is_prediction'] is False

def test_invalid_grades_ignored():
    r=analyze_student([],[{'score':200,'max_score':100},{'score':50,'max_score':0}])
    assert r['valid_assessments']==0 and r['risk_index'] is None

def test_aggregate():
    a=analyze_student([],[]); b=analyze_student([{'status':'absent'}]*4,[{'score':10,'max_score':100}])
    assert aggregate_reports([a,b])['needs_human_review']==1
