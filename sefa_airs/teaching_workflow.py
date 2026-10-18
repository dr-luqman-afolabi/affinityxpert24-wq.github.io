"""Deterministic checks for lecturer teaching plans and weekly evidence."""
from datetime import date

def validate_plan_rows(rows, max_week=52):
    if not rows or len(rows)>500: raise ValueError('Teaching plan must have 1-500 rows')
    clean=[]; seen=set()
    for n,row in enumerate(rows,2):
        try:
            week=int(row['week_no']); topic=str(row['planned_topic']).strip()
            hours=float(row['planned_hours'])
            if not (1<=week<=max_week and topic and len(topic)<=300 and 0<hours<=100):
                raise ValueError('invalid week, topic or hours')
            key=(week,topic.casefold())
            if key in seen: raise ValueError('duplicate topic in week')
            seen.add(key);clean.append((week,topic,hours))
        except (KeyError,ValueError,TypeError) as exc:
            raise ValueError(f'Row {n}: {exc}') from exc
    return clean

def coverage_alerts(plan_rows, today_week, target=85):
    """Rows: week_no, planned_hours, delivered_hours, status. No rows => unknown."""
    if not plan_rows:return {'status':'no_plan','alerts':['Teaching plan has not been uploaded'],'expected_percent':None,'verified_percent':None}
    total=sum(float(r['planned_hours']) for r in plan_rows)
    if total<=0:return {'status':'no_plan','alerts':['Teaching plan has no planned hours'],'expected_percent':None,'verified_percent':None}
    expected=sum(float(r['planned_hours']) for r in plan_rows if int(r['week_no'])<=today_week)
    verified=sum(min(float(r['planned_hours']),float(r.get('delivered_hours') or 0)) for r in plan_rows if r.get('status')=='approved')
    pending=sum(1 for r in plan_rows if int(r['week_no'])<=today_week and r.get('status') in ('planned','submitted','ta_verified'))
    alerts=[]
    if pending:alerts.append(f'{pending} due topic reports awaiting completion or HOD approval')
    if verified+1e-8<expected:alerts.append('Verified delivery is behind scheduled teaching pace')
    if today_week>=max(int(r['week_no']) for r in plan_rows) and verified/total*100<target:alerts.append(f'Final verified coverage below {target:g}% target')
    return {'status':'attention' if alerts else 'on_track','alerts':alerts,'expected_percent':round(expected/total*100,1),'verified_percent':round(verified/total*100,1)}
