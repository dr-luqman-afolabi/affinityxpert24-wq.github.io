"""LMS (Moodle) evidence: spreadsheet exports or the Moodle Web Services REST API.

LMS engagement is shown as context for staff review; it does not change the risk index.
Grades imported from the LMS become ordinary assessment records (earned/possible points).
"""
import re
from datetime import date, datetime, timezone

ID_COLUMNS = ('student_no', 'id number', 'idnumber', 'username')
NEVER = {'', 'never', '-', 'none', 'n/a'}


def _number(value, field, minimum=0.0):
    if value is None or str(value).strip() == '':
        return None
    try:
        number = float(str(value).replace('%', '').replace(',', '').strip())
    except ValueError:
        raise ValueError(f'{field} must be a number')
    if number < minimum:
        raise ValueError(f'{field} cannot be negative')
    return number


def _day(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or '').strip()
    if text.lower() in NEVER:
        return None
    return date.fromisoformat(text[:10]).isoformat()


def parse_engagement_rows(rows):
    """Generic engagement sheet: student_no,last_access[,activities_completed,activities_total,minutes_active]."""
    if not rows or not {'student_no', 'last_access'}.issubset(rows[0]):
        raise ValueError('Required columns: student_no,last_access (optional: activities_completed,activities_total,minutes_active)')
    if len(rows) > 5000:
        raise ValueError('Maximum 5000 rows per file')
    records, errors, seen = [], [], set()
    for line, row in enumerate(rows, 2):
        try:
            number = str(row.get('student_no') or '').strip()
            if not number:
                raise ValueError('missing student_no')
            if number in seen:
                raise ValueError('duplicate student_no')
            seen.add(number)
            done = _number(row.get('activities_completed'), 'activities_completed')
            total = _number(row.get('activities_total'), 'activities_total')
            if done is not None and total is not None and done > total:
                raise ValueError('activities_completed is larger than activities_total')
            records.append({'student_no': number, 'last_access': _day(row.get('last_access')),
                            'activities_completed': int(done) if done is not None else None,
                            'activities_total': int(total) if total is not None else None,
                            'minutes_active': _number(row.get('minutes_active'), 'minutes_active')})
        except ValueError as exc:
            errors.append(f'Row {line}: {exc}')
    return records, errors


def _kind(item):
    lowered = item.lower()
    if lowered.startswith('quiz'):
        return 'quiz'
    if lowered.startswith('assignment'):
        return 'assignment'
    return 'lms'


def parse_grade_rows(rows):
    """Moodle gradebook export with *(Percentage)* columns, or a generic student_no,item,score,max_score sheet.

    Header case is preserved so item names stay readable. Blank and '-' grades are skipped, never zero.
    """
    if not rows:
        raise ValueError('The file has no rows')
    headers = {h.strip().lower(): h for h in rows[0] if h}
    records, errors = [], []
    if {'student_no', 'item', 'score', 'max_score'}.issubset(headers):
        for line, row in enumerate(rows, 2):
            try:
                number = str(row.get(headers['student_no']) or '').strip()
                item = str(row.get(headers['item']) or '').strip()
                score = _number(row.get(headers['score']), 'score')
                maximum = _number(row.get(headers['max_score']), 'max_score')
                if not number or not item:
                    raise ValueError('student_no and item are required')
                if score is None:
                    continue
                if not maximum or score > maximum:
                    raise ValueError('score must be between 0 and max_score')
                records.append({'student_no': number, 'item': item[:90], 'kind': _kind(item), 'score': score, 'max_score': maximum})
            except ValueError as exc:
                errors.append(f'Row {line}: {exc}')
        return records, errors
    id_column = next((headers[c] for c in ID_COLUMNS if c in headers), None)
    if id_column is None:
        raise ValueError('Add an "ID number" (student number) column, or use the student_no,item,score,max_score template')
    grade_columns = [h for key, h in headers.items() if key.endswith('(percentage)') and not key.startswith('course total')]
    if not grade_columns:
        raise ValueError('No "(Percentage)" grade columns found. In Moodle, export grades with display type "Percentage"')
    for line, row in enumerate(rows, 2):
        number = str(row.get(id_column) or '').strip()
        if not number:
            continue
        for column in grade_columns:
            raw = str(row.get(column) or '').strip()
            if raw.lower() in NEVER:
                continue
            try:
                score = _number(raw, column)
                if score > 100:
                    raise ValueError(f'{column} is above 100%')
            except ValueError as exc:
                errors.append(f'Row {line}: {exc}')
                continue
            item = re.sub(r'\s*\(percentage\)\s*$', '', column, flags=re.I).strip()
            records.append({'student_no': number, 'item': item[:90], 'kind': _kind(item), 'score': score, 'max_score': 100.0})
    return records, errors


class MoodleError(Exception):
    pass


class MoodleClient:
    """Minimal Moodle Web Services client (REST protocol, JSON format)."""

    def __init__(self, base_url, token, transport=None, timeout=30):
        if not base_url or not token:
            raise MoodleError('Moodle is not configured. Set MOODLE_URL and MOODLE_TOKEN.')
        self.endpoint = base_url.rstrip('/') + '/webservice/rest/server.php'
        self.token, self.transport, self.timeout = token, transport, timeout

    def call(self, function, **params):
        import httpx
        query = {'wstoken': self.token, 'wsfunction': function, 'moodlewsrestformat': 'json', **params}
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
                response = client.post(self.endpoint, data=query)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MoodleError(f'Could not reach Moodle: {exc}') from exc
        if isinstance(data, dict) and data.get('exception'):
            raise MoodleError(f"Moodle refused {function}: {data.get('message') or data.get('errorcode')}")
        return data

    def course_evidence(self, course_id):
        """Return (engagement, grades) keyed by Moodle idnumber/username for one Moodle course."""
        users = self.call('core_enrol_get_enrolled_users', courseid=course_id)
        keys = {}
        engagement = []
        for user in users:
            candidates = [str(user.get('idnumber') or '').strip(), str(user.get('username') or '').strip()]
            keys[user['id']] = [c for c in candidates if c]
            stamp = user.get('lastcourseaccess') or 0
            engagement.append({'keys': keys[user['id']],
                               'last_access': datetime.fromtimestamp(stamp, timezone.utc).date().isoformat() if stamp else None,
                               'activities_completed': None, 'activities_total': None, 'minutes_active': None})
        grades = []
        report = self.call('gradereport_user_get_grade_items', courseid=course_id)
        for usergrade in report.get('usergrades', []):
            for item in usergrade.get('gradeitems', []):
                if item.get('itemtype') != 'mod' or item.get('graderaw') is None or not item.get('grademax'):
                    continue
                name = str(item.get('itemname') or item.get('itemmodule') or 'LMS item')
                kind = {'quiz': 'quiz', 'assign': 'assignment'}.get(item.get('itemmodule'), 'lms')
                grades.append({'keys': keys.get(usergrade.get('userid'), []), 'item': name[:90], 'kind': kind,
                               'score': float(item['graderaw']), 'max_score': float(item['grademax'])})
        return engagement, grades


def days_since(day, today=None):
    if not day:
        return None
    return ((today or date.today()) - date.fromisoformat(day)).days
