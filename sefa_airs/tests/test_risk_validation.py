from risk_validation import validate_outcomes, quality_report

def test_small_cohort_suppressed():
    result=validate_outcomes([{'risk_band':'high','outcome':1}])
    assert not result['validated'] and 'precision' not in result

def test_confusion_matrix_and_unknown():
    rows=([{'risk_band':'high','outcome':1}]*10 +
          [{'risk_band':'high','outcome':0}]*5 +
          [{'risk_band':'low','outcome':1}]*5 +
          [{'risk_band':'low','outcome':0}]*10 +
          [{'risk_band':'insufficient data','outcome':1}])
    result=validate_outcomes(rows)
    assert result['confusion_matrix']=={'tp':10,'fp':5,'tn':10,'fn':5}
    assert result['excluded_insufficient_evidence']==1
    assert result['precision']==round(10/15,4)

def test_no_implicit_missing_as_negative():
    result=validate_outcomes([{'risk_band':'critical','outcome':None}]*40)
    assert result['labeled_rows']==0 and not result['validated']

def test_quality_report():
    q=quality_report([{'risk_band':'high','evidence_sources':2,'recorded_sessions':5,'valid_assessments':1},
                      {'risk_band':'insufficient data','evidence_sources':0,'recorded_sessions':0,'valid_assessments':0}])
    assert q['complete_evidence']==1 and q['insufficient_data']==1
