"""Aggregate only scoped course offering records, never infer missing attendance as absence."""
def summarize_offerings(rows):
    values=[r['coverage'] for r in rows if r['coverage'] is not None]
    return {'courses':len(rows),'enrolments':sum(r['enrolled'] for r in rows),
            'average_coverage':round(sum(values)/len(values),1) if values else None,
            'below_target':sum(v<85 for v in values),'without_coverage':len(rows)-len(values),
            'without_attendance':sum(r['attendance'] is None for r in rows)}
