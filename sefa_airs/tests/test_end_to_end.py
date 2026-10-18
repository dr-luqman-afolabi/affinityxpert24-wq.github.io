"""HTTP-level workflow tests: float -> offering -> roster -> attendance -> teaching approval -> analytics."""
import re
import pytest
from fastapi.testclient import TestClient
import app as A

PASSWORD = 'password12345'
CSV = 'text/csv'


def _client():
    return TestClient(A.app, raise_server_exceptions=False)


def _token(c, path='/'):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get(path).text).group(1)


def _login(username):
    c = _client()
    r = c.post('/login', data={'username': username, 'password': PASSWORD, 'csrf_token': _token(c)}, follow_redirects=False)
    assert r.status_code == 303
    return c, _token(c)


@pytest.fixture(scope='module')
def world():
    s = A.SessionLocal()
    for name, role, programme in [('e2e_admin', 'admin', None), ('e2e_lect', 'lecturer', 'Finance'),
                                  ('e2e_ta', 'ta', 'Finance'), ('e2e_hod', 'hod', 'Finance')]:
        if not s.query(A.User).filter_by(username=name).first():
            s.add(A.User(username=name, password_hash=A.crypt.hash(PASSWORD), role=role, programme=programme))
    s.commit()
    lect = s.query(A.User).filter_by(username='e2e_lect').one().id
    ta = s.query(A.User).filter_by(username='e2e_ta').one().id
    s.close()
    admin, t = _login('e2e_admin')
    module = admin.get('/api/curriculum-catalogue?programme=Finance').json()['modules'][0]
    assert admin.post('/api/float-module', data={'programme': 'Finance', 'module_code': module['module_code'], 'academic_year': '2026/2027',
                      'intake': 'E2E', 'session_type': 'morning', 'module_block': 'M1', 'csrf_token': t}).status_code == 200
    form = {'code': module['module_code'], 'title': module['module_title'], 'programme': 'Finance', 'academic_year': '2026/2027',
            'session_type': 'morning', 'intake': 'E2E', 'module': 'M1', 'start_date': '2026-10-05', 'end_date': '2026-10-30',
            'weeks': '4', 'lecturer_id': str(lect), 'csrf_token': t}
    assert admin.post('/courses', data=form, follow_redirects=False).status_code == 303
    s = A.SessionLocal()
    cid = s.query(A.Course).filter(A.Course.code.like(f"{module['module_code']}-E2E-%")).one().id
    s.close()
    assert admin.post('/ta-assignments', data={'ta_id': ta, 'course_id': cid, 'csrf_token': t}, follow_redirects=False).status_code == 303
    return {'admin': (admin, t), 'cid': cid, 'form': form}


def test_duplicate_offering_is_conflict_not_crash(world):
    admin, _ = world['admin']
    assert admin.post('/courses', data=world['form'], follow_redirects=False).status_code == 409


def test_unassigned_lecturer_is_accepted(world):
    admin, t = world['admin']
    form = dict(world['form'], module='M2', lecturer_id='', csrf_token=t)
    admin.post('/api/float-module', data={'programme': 'Finance', 'module_code': form['code'], 'academic_year': '2026/2027',
               'intake': 'E2E', 'session_type': 'morning', 'module_block': 'M2', 'csrf_token': t})
    assert admin.post('/courses', data=form, follow_redirects=False).status_code == 303


def test_full_course_workflow(world):
    cid = world['cid']
    admin, t = world['admin']
    r = admin.post(f'/api/courses/{cid}/credits', data={'credits': '10', 'csrf_token': t}, headers={'accept': 'text/html'}, follow_redirects=False)
    assert r.status_code == 303
    ta, tt = _login('e2e_ta')
    roster = b'Student_No ,name,programme\nE1,One,Finance\nE2,Two,Finance\n'
    r = ta.post(f'/courses/{cid}/imports/preview', data={'kind': 'profiles', 'csrf_token': tt}, files={'file': ('r.csv', roster, CSV)})
    token = re.search(r'/imports/([^/]+)/confirm', r.text).group(1)
    assert ta.post(f'/courses/{cid}/imports/{token}/confirm', data={'csrf_token': tt}, follow_redirects=False).status_code == 303
    att = b'student_no,session_date,status\nE1,2026-10-05,present\nE2,2026-10-05,absent\n'
    r = ta.post(f'/courses/{cid}/imports/preview', data={'kind': 'attendance', 'csrf_token': tt}, files={'file': ('a.csv', att, CSV)})
    token = re.search(r'/imports/([^/]+)/confirm', r.text).group(1)
    assert ta.post(f'/courses/{cid}/imports/{token}/confirm', data={'csrf_token': tt}, follow_redirects=False).status_code == 303

    lect, lt = _login('e2e_lect')
    r = lect.post(f'/courses/{cid}/teaching-plan/import', data={'csrf_token': lt}, files={'file': ('p.csv', b'week_no,planned_topic,planned_hours\n1,Intro,3\n', CSV)})
    assert r.status_code == 200
    item = lect.get(f'/api/courses/{cid}/teaching-plan').json()['topics'][0]['id']
    assert lect.post(f'/api/teaching-plan/{item}/report', data={'delivered_hours': '3', 'csrf_token': lt}).status_code == 200
    assert ta.post(f'/api/teaching-plan/{item}/ta-review', data={'decision': 'verify', 'csrf_token': tt}).status_code == 200
    hod, ht = _login('e2e_hod')
    assert hod.post(f'/api/teaching-plan/{item}/hod-review', data={'decision': 'approve', 'csrf_token': ht}).json()['status'] == 'approved'

    for path in [f'/courses/{cid}', '/', '/monitor', '/monitor.csv', '/ai-risk', f'/api/courses/{cid}/ai-risk',
                 f'/api/courses/{cid}/ai-risk.csv', f'/api/courses/{cid}/weekly-trends', f'/api/courses/{cid}/academic-monitor?as_of=',
                 '/api/academic-monitor', '/api/dashboard', f'/api/courses/{cid}/ai-brief']:
        assert lect.get(path).status_code == 200, path


@pytest.mark.parametrize('body', [b'', b'foo,bar\n1,2\n'])
def test_malformed_attendance_preview_is_rejected_cleanly(world, body):
    ta, tt = _login('e2e_ta')
    r = ta.post(f"/courses/{world['cid']}/imports/preview", data={'kind': 'attendance', 'csrf_token': tt}, files={'file': ('a.csv', body, CSV)})
    assert r.status_code == 200 and 'Import blocked' in r.text


def test_browser_errors_are_friendly():
    c = _client()
    assert c.get('/monitor', headers={'accept': 'text/html'}, follow_redirects=False).headers['location'] == '/'
    assert c.get('/monitor').status_code == 401
    r = c.post('/login', data={'username': 'x', 'password': 'y', 'csrf_token': 'stale'})
    assert r.status_code == 403 and 'expired' in r.text
