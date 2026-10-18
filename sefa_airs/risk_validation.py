"""Offline validation of support triage against consented, historical outcome labels.
No training, automated decisions, or demographic profiling.
"""
from collections import Counter

BANDS=('low','moderate','high','critical','insufficient data')

def validate_outcomes(rows, threshold='high', min_labeled=30):
    """Rows: risk_band, outcome (0/1). An outcome of 1 denotes adverse academic outcome.
    Missing or unknown outcomes are excluded. Suppress small-cohort metrics.
    """
    if threshold not in ('moderate','high','critical'):
        raise ValueError('Unsupported threshold')
    eligible=[r for r in rows if r.get('risk_band') in BANDS and type(r.get('outcome')) is int and r['outcome'] in (0,1)]
    scored=[r for r in eligible if r['risk_band']!='insufficient data']
    output={'total_rows':len(rows),'labeled_rows':len(eligible),'scored_rows':len(scored),
            'excluded_unknown_outcomes':len(rows)-len(eligible),
            'excluded_insufficient_evidence':len(eligible)-len(scored),
            'minimum_labeled':min_labeled,'threshold':threshold,'validated':False,
            'warning':'Retrospective descriptive validation only; not a prediction of individual failure.'}
    if len(scored)<min_labeled:
        output['reason']='Insufficient labeled and scored records for reporting validation metrics'
        return output
    cutoff=BANDS.index(threshold)
    tp=fp=tn=fn=0
    for row in scored:
        flag=BANDS.index(row['risk_band'])>=cutoff
        if flag and row['outcome']==1: tp+=1
        elif flag: fp+=1
        elif row['outcome']==1: fn+=1
        else: tn+=1
    div=lambda a,b: round(a/b,4) if b else None
    output.update({'confusion_matrix':{'tp':tp,'fp':fp,'tn':tn,'fn':fn},
        'precision':div(tp,tp+fp),'recall':div(tp,tp+fn),'specificity':div(tn,tn+fp),
        'false_positive_rate':div(fp,fp+tn),'positive_predictive_value':div(tp,tp+fp),
        'base_rate':div(tp+fn,len(scored)),
        'validated':True,'reason':'Retrospective discrimination metrics computed; calibration, temporal and fairness audits remain required.'})
    return output

def quality_report(student_reports):
    counts=Counter(r.get('risk_band','insufficient data') for r in student_reports)
    n=len(student_reports)
    return {'total':n,'insufficient_data':counts['insufficient data'],
        'single_source':sum(r.get('evidence_sources',0)==1 for r in student_reports),
        'no_attendance':sum(r.get('recorded_sessions',0)==0 for r in student_reports),
        'no_assessments':sum(r.get('valid_assessments',0)==0 for r in student_reports),
        'complete_evidence':sum(r.get('evidence_sources',0)==2 for r in student_reports),
        'completeness_percent':round(100*sum(r.get('evidence_sources',0)==2 for r in student_reports)/n,1) if n else None}
