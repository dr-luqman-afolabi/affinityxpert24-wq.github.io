from dashboard_summary import summarize_offerings

def test_missing_data_not_zero():
    result=summarize_offerings([{'coverage':None,'enrolled':4,'attendance':None}])
    assert result['average_coverage'] is None
    assert result['below_target']==0
    assert result['without_attendance']==1

def test_aggregate():
    rows=[{'coverage':60,'enrolled':20,'attendance':70},{'coverage':90,'enrolled':30,'attendance':None}]
    x=summarize_offerings(rows)
    assert x['average_coverage']==75 and x['below_target']==1 and x['enrolments']==50
