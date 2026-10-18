"""Validation helpers for staged SEFA-AIRS spreadsheet imports."""
from datetime import date, datetime


def attendance_rows(rows, enrolled):
    if not rows or not {'student_no', 'session_date', 'status'}.issubset(rows[0]):
        raise ValueError('Required columns: student_no,session_date,status')
    if len(rows)>10000:
        raise ValueError('Maximum 10000 attendance rows')
    output, errors, seen = [], [], set()
    for line, row in enumerate(rows, 2):
        try:
            number = str(row.get('student_no') or '').strip()
            raw_day = row.get('session_date')
            if isinstance(raw_day, datetime): day=raw_day.date().isoformat()
            elif isinstance(raw_day, date): day=raw_day.isoformat()
            else: day=str(raw_day or '').strip()
            date.fromisoformat(day)
            status=str(row.get('status') or '').strip().lower()
            if status not in ('present','absent','late'): raise ValueError('invalid attendance status')
            if number not in enrolled: raise ValueError('student is not enrolled in this course offering')
            if (number,day) in seen: raise ValueError('duplicate student/date in spreadsheet')
            seen.add((number,day))
            output.append({'student_no':number,'session_date':day,'status':status})
        except Exception as exc: errors.append(f'Row {line}: {exc}')
    return output,errors


def profile_rows(rows, programme, existing, validate_roster):
    try: clean=validate_roster(rows,programme)
    except ValueError as exc: return [],[str(exc)]
    errors=[]
    for i, record in enumerate(clean,2):
        old=existing.get(record['student_no'])
        if old and (old['name']!=record['name'] or old['programme']!=record['programme']):
            errors.append(f"Row {i}: conflicting identity for {record['student_no']}")
        if old:
            for field in ('email','phone','intake','session'):
                if record[field] and old.get(field) and record[field]!=old[field]:
                    errors.append(f"Row {i}: existing {field} conflicts for {record['student_no']}")
    return clean,errors
