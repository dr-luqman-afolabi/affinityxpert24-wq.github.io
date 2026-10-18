"""Explainable academic-support triage; never an automated disciplinary decision."""
from collections import Counter
from datetime import date
VALID_ATTENDANCE={'present','late','absent'}

def analyze_student(attendance, assessments, interventions=(), today=None, scheduled_dates=None):
    """Assess recorded evidence; if a calendar is supplied, exclude unscheduled entries.

    Assessment percentage is total earned points / total possible points, rather than
    an unweighted average of percentages. This is *not* a university-approved
    CAT/exam weighting scheme; only recorded points are used.
    """
    today=today or date.today()
    scheduled=set(scheduled_dates) if scheduled_dates is not None else None
    seen=set(); valid=[]; ignored=0
    for a in attendance:
        day=a.get('date') or a.get('session_date')
        if a.get('status') not in VALID_ATTENDANCE or (scheduled is not None and day not in scheduled):
            ignored+=1;continue
        if day and day in seen:
            ignored+=1;continue
        if day:seen.add(day)
        valid.append(a)
    recorded=len(valid)
    attended=sum(a['status'] in ('present','late') for a in valid)
    absent=sum(a['status']=='absent' for a in valid)
    late=sum(a['status']=='late' for a in valid)
    attendance_pct=round(100*attended/recorded,1) if recorded else None
    grades=[g for g in assessments if type(g.get('score')) in (int,float) and type(g.get('max_score')) in (int,float) and 0<g['max_score']<=100000 and 0<=g['score']<=g['max_score']]
    assessment_pct=round(100*sum(g['score'] for g in grades)/sum(g['max_score'] for g in grades),1) if grades else None
    reasons=[];components=[]
    if recorded>=3:
        components.append((100-attendance_pct,.4))
        if attendance_pct<75:reasons.append('Recorded attendance below 75%')
        if absent>=2:reasons.append('At least two recorded absences')
    elif recorded:reasons.append('Fewer than three recorded attendance entries; attendance evidence limited')
    else:reasons.append('No attendance records available')
    if grades:
        components.append((100-assessment_pct,.6))
        if assessment_pct<50:reasons.append('Recorded assessment points below 50%')
    else:reasons.append('No valid assessments recorded')
    if ignored:reasons.append('Invalid, duplicate or unscheduled attendance entries excluded')
    risk=round(sum(v*w for v,w in components)/sum(w for _,w in components),1) if components else None
    label='insufficient data' if risk is None else ('low' if risk<25 else 'moderate' if risk<50 else 'high' if risk<75 else 'critical')
    if risk is not None and len(components)==1:reasons.append('Single evidence source; provisional classification')
    open_cases=sum(str(i.get('status','open')).lower() not in ('closed','resolved') for i in interventions)
    if open_cases:reasons.append('Existing open academic-support follow-up')
    if risk is None:actions=['Check data completeness with the assigned TA before assessing support needs']
    elif risk>=75:actions=['Arrange a confidential lecturer/HOD review promptly','Offer an individual academic-support meeting','Agree a documented follow-up date']
    elif risk>=50:actions=['Invite the student to a supportive check-in','Review attendance and assessment evidence with the lecturer']
    elif risk>=25:actions=['Offer targeted study support','Review progress after the next assessment']
    else:actions=['Continue ordinary academic support and monitor subsequent records']
    if open_cases:actions.append('Review existing intervention before opening another case')
    return {'risk_index':risk,'risk_band':label,'attendance_percent':attendance_pct,'assessment_percent':assessment_pct,'recorded_sessions':recorded,'recorded_absences':absent,'recorded_late':late,'excluded_attendance_entries':ignored,'valid_assessments':len(grades),'open_interventions':open_cases,'evidence_sources':len(components),'reasons':reasons,'suggested_support':actions,'model_type':'explainable_rules_v2','is_prediction':False,'requires_human_review':True,'limitations':'Not a validated probability of dropout or failure. Assessment uses earned/possible points, not approved component weights. Missing registers are not absences.'}

def aggregate_reports(reports):
    bands=Counter(r['risk_band'] for r in reports)
    return {'total':len(reports),'risk_bands':{k:bands[k] for k in ('low','moderate','high','critical','insufficient data')},'open_interventions':sum(r['open_interventions'] for r in reports),'needs_human_review':sum(r['risk_band'] in ('high','critical') for r in reports),'model_type':'explainable_rules_v2','warning':'Support triage only; not a predictive ML model.'}
