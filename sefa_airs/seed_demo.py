"""Create demo accounts and made-up data in a NEW, empty database. Never run on real data.

Runs the normal web workflows in-process, so every record passes the app's own validation.
"""
import random, re
from datetime import date, timedelta
from fastapi.testclient import TestClient
import app as A

ADMIN_PW = 'DemoAdmin2026!'
PW = 'DemoPass2026!'
NAMES = ['Aline Uwase', 'Jean Mugisha', 'Grace Ingabire', 'Eric Niyonzima', 'Diane Mukamana', 'Patrick Habimana',
         'Claudine Uwimana', 'Samuel Nkurunziza', 'Esther Umutoni', 'David Hakizimana', 'Alice Nyirahabimana', 'Kevin Ndayisaba']


def login(username, password=PW):
    c = TestClient(A.app)
    t = re.search(r'name="csrf_token" value="([^"]+)"', c.get('/').text).group(1)
    c.post('/login', data={'username': username, 'password': password, 'csrf_token': t})
    return c, re.search(r'name="csrf_token" value="([^"]+)"', c.get('/').text).group(1)


def confirm(client, cid, token, response):
    client.post(f'/courses/{cid}/imports/{re.search(r"/imports/([^/]+)/confirm", response.text).group(1)}/confirm',
                data={'csrf_token': token})


def main():
    s = A.SessionLocal()
    if s.query(A.User).count():
        raise SystemExit('Database already has users; demo data is only loaded into a new, empty database.')
    s.add(A.User(username='admin', password_hash=A.crypt.hash(ADMIN_PW), role='admin')); s.commit(); s.close()
    a, t = login('admin', ADMIN_PW)
    for u, r, p in [('dean', 'dean', ''), ('hod.finance', 'hod', 'Finance'), ('lecturer.finance', 'lecturer', 'Finance'), ('ta.finance', 'ta', 'Finance')]:
        a.post('/users', data={'username': u, 'password': PW, 'role': r, 'programme': p, 'csrf_token': t})
    mods = a.get('/api/curriculum-catalogue?programme=Finance').json()['modules']
    home = a.get('/').text
    lect = re.search(r'<option value="(\d+)">lecturer\.finance', home).group(1)
    for m, sess in [(mods[5], 'morning'), (mods[8], 'evening')]:
        a.post('/api/float-module', data={'programme': 'Finance', 'module_code': m['module_code'], 'academic_year': '2026/2027', 'intake': '2026-09',
               'session_type': sess, 'module_block': 'M3', 'csrf_token': t})
        a.post('/courses', data={'code': m['module_code'], 'title': m['module_title'], 'programme': 'Finance', 'academic_year': '2026/2027',
               'session_type': sess, 'intake': '2026-09', 'module': 'M3', 'start_date': '2026-09-28', 'end_date': '2026-10-23',
               'weeks': '4', 'lecturer_id': lect, 'csrf_token': t})
    home = a.get('/').text
    cids = sorted(set(re.findall(r'href="/courses/(\d+)"', home)))
    ta_id = re.search(r'<option value="(\d+)">ta\.finance', home).group(1)
    for cid in cids:
        a.post('/ta-assignments', data={'ta_id': ta_id, 'course_id': cid, 'csrf_token': t})
        a.post(f'/api/courses/{cid}/credits', data={'credits': '10', 'csrf_token': t})
    random.seed(7)
    ta, tt = login('ta.finance'); lc, lt = login('lecturer.finance'); hc, ht = login('hod.finance')
    days = [d for d in (date(2026, 9, 28) + timedelta(n) for n in range(20)) if d.weekday() < 5][:8]
    for k, cid in enumerate(cids):
        sess = 'morning' if k == 0 else 'evening'
        roster = 'student_no,name,programme,email,intake,session\n' + ''.join(
            f'DEMO{k}{i:02d},{n},Finance,demo{k}{i}@example.test,2026-09,{sess}\n' for i, n in enumerate(NAMES))
        confirm(ta, cid, tt, ta.post(f'/courses/{cid}/imports/preview', data={'kind': 'profiles', 'csrf_token': tt},
                                     files={'file': ('roster.csv', roster.encode(), 'text/csv')}))
        att = 'student_no,session_date,status\n'
        for i in range(len(NAMES)):
            p = 0.95 if i % 4 else 0.55
            for d in days:
                att += f'DEMO{k}{i:02d},{d},{random.choices(["present", "late", "absent"], [p * 0.9, p * 0.1, 1 - p])[0]}\n'
        confirm(ta, cid, tt, ta.post(f'/courses/{cid}/imports/preview', data={'kind': 'attendance', 'csrf_token': tt},
                                     files={'file': ('attendance.csv', att.encode(), 'text/csv')}))
        sids = re.findall(r'<option value="(\d+)">DEMO', lc.get(f'/courses/{cid}').text)[:len(NAMES)]
        for i, sid in enumerate(sids):
            lc.post(f'/courses/{cid}/grades', data={'student_id': sid, 'kind': 'cat', 'title': 'CAT 1',
                    'value': str(random.randint(8, 14) if i % 4 == 0 else random.randint(17, 28)), 'maximum': '30', 'csrf_token': lt})
        plan = b'week_no,planned_topic,planned_hours\n1,Foundations and scope,15\n2,Core models,15\n3,Applications and cases,15\n4,Revision and synthesis,15\n'
        lc.post(f'/courses/{cid}/teaching-plan/import', data={'csrf_token': lt}, files={'file': ('plan.csv', plan, 'text/csv')})
        lc.post(f'/courses/{cid}/weekly/import', data={'csrf_token': lt}, files={'file': ('weekly.csv',
                b'week_no,planned_topic,planned_hours,delivered_hours,delivery_notes\n1,Foundations and scope,15,15,Done\n'
                b'2,Core models,15,12,Partial\n3,Applications and cases,15,0,\n4,Revision and synthesis,15,0,\n', 'text/csv')})
        items = lc.get(f'/api/courses/{cid}/teaching-plan').json()['topics']
        for item, hours in zip(items[:2], (15, 12)):
            lc.post(f"/api/teaching-plan/{item['id']}/report", data={'delivered_hours': str(hours), 'notes': 'Delivered as planned', 'csrf_token': lt})
        ta.post(f"/api/teaching-plan/{items[0]['id']}/ta-review", data={'decision': 'verify', 'csrf_token': tt})
        hc.post(f"/api/teaching-plan/{items[0]['id']}/hod-review", data={'decision': 'approve', 'csrf_token': ht})
    print('Demo data loaded (made-up students only).')
    print(f'  admin / {ADMIN_PW}')
    for u in ('dean', 'hod.finance', 'lecturer.finance', 'ta.finance'):
        print(f'  {u} / {PW}')


if __name__ == '__main__':
    main()
