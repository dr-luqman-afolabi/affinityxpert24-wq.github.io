import pytest
from teaching_workflow import validate_plan_rows, coverage_alerts

def test_plan_validation():
    assert validate_plan_rows([{'week_no':'1','planned_topic':'Demand','planned_hours':'3'}])==[(1,'Demand',3.0)]
    with pytest.raises(ValueError):validate_plan_rows([{'week_no':'1','planned_topic':'Demand','planned_hours':'3'},{'week_no':'1','planned_topic':'demand','planned_hours':'2'}])

def test_approval_counts_only_approved():
    rows=[{'week_no':1,'planned_hours':3,'delivered_hours':3,'status':'approved'}, {'week_no':2,'planned_hours':3,'delivered_hours':3,'status':'submitted'}]
    result=coverage_alerts(rows,2)
    assert result['verified_percent']==50
    assert result['expected_percent']==100
    assert result['status']=='attention'

def test_missing_plan_unknown():
    assert coverage_alerts([],1)['verified_percent'] is None
