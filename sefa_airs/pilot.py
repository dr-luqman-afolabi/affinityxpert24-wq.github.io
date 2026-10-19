"""Pilot-phase evaluation: usage feature names and the capability benchmark.

The benchmark compares this pilot with capabilities typically expected of a
university early-alert / learning-analytics system. Statuses are honest
self-assessments of this codebase, not certification.
"""
import os
import re

FEATURES = [
    ('/', 'Academic overview'),
    ('/monitor', 'Academic monitoring'),
    ('/monitor.csv', 'Monitoring export'),
    ('/ai-risk', 'Risk analytics'),
    ('/api/courses/{course_id}/ai-risk.csv', 'Risk export'),
    ('/courses/{course_id}', 'Course page'),
    ('/courses/{course_id}/imports/preview', 'Spreadsheet import'),
    ('/courses/{course_id}/imports/{token}/confirm', 'Spreadsheet import'),
    ('/courses/{course_id}/attendance', 'Attendance entry'),
    ('/courses/{course_id}/grades', 'Assessment entry'),
    ('/courses/{course_id}/interventions', 'Interventions'),
    ('/courses/{course_id}/teaching-plan/import', 'Teaching plan workflow'),
    ('/api/teaching-plan/{item_id}/report', 'Teaching plan workflow'),
    ('/api/teaching-plan/{item_id}/ta-review', 'Teaching plan workflow'),
    ('/api/teaching-plan/{item_id}/hod-review', 'Teaching plan workflow'),
    ('/courses/{course_id}/weekly/import', 'Weekly coverage'),
    ('/courses/{course_id}/lms/engagement', 'LMS import'),
    ('/courses/{course_id}/lms/grades', 'LMS import'),
    ('/courses/{course_id}/lms/sync', 'LMS sync'),
    ('/courses', 'Course set-up'),
    ('/api/courses/{course_id}/credits', 'Course set-up'),
    ('/users', 'User management'),
    ('/curricula/{curriculum_id}', 'Curriculum archive'),
    ('/api/courses/{course_id}/risk.csv', 'Risk export'),
    ('/courses/{course_id}/students', 'Spreadsheet import'),
    ('/courses/{course_id}/attendance/import', 'Spreadsheet import'),
    ('/courses/{course_id}/topics', 'Topic coverage'),
    ('/topics/{topic_id}/progress', 'Topic coverage'),
    ('/api/courses/{course_id}/academic-monitor', 'Academic monitoring report'),
    ('/api/courses/{course_id}/weekly-coverage', 'Weekly coverage'),
    ('/api/weekly-coverage', 'Weekly coverage'),
    ('/api/float-module', 'Course set-up'),
    ('/ta-assignments', 'Course set-up'),
    ('/curricula', 'Curriculum upload'),
    ('/pilot', 'Pilot evaluation'),
    ('/pilot/{dataset}.csv', 'Pilot export'),
    ('/courses/{course_id}/lms/link', 'LMS sync'),
    ('/feedback', 'Feedback'),
]
_FEATURE_BY_PATH = dict(FEATURES)
FEEDBACK_FEATURES = sorted({name for _, name in FEATURES} | {'Sign-in', 'Overall system'})


def feature_name(path_template):
    return _FEATURE_BY_PATH.get(path_template) or re.sub(r'\{[^}]+\}', '…', path_template)[:100]


IMPLEMENTED, PARTIAL, MISSING = 'implemented', 'partial', 'not yet'
SCORE = {IMPLEMENTED: 1.0, PARTIAL: 0.5, MISSING: 0.0}


def benchmark(lms_connected=False, lms_evidence=False, https=False):
    """Capability checklist. A few rows reflect live configuration."""
    rows = [
        ('Data capture', 'Attendance registers (manual and spreadsheet)', IMPLEMENTED, 'Preview-and-confirm imports; missing registers are never counted as absences.'),
        ('Data capture', 'Assessment marks', IMPLEMENTED, 'Manual entry and LMS grade import. Approved CAT/exam weighting not yet configured.'),
        ('Data capture', 'Teaching coverage with verification', IMPLEMENTED, 'Lecturer report, TA verification, HOD approval.'),
        ('Data capture', 'LMS engagement and grades (Moodle)',
         IMPLEMENTED if lms_connected and lms_evidence else PARTIAL,
         'Live Moodle API sync is configured and in use.' if lms_connected and lms_evidence else
         'Spreadsheet import available; set MOODLE_URL and MOODLE_TOKEN for automatic sync.'),
        ('Data capture', 'Student information system / ERP integration', MISSING, 'Rosters are uploaded manually.'),
        ('Data capture', 'Library, finance or welfare signals', MISSING, 'Requires institutional approval before inclusion.'),
        ('Analytics', 'Explainable rule-based support triage', IMPLEMENTED, 'Every band lists its reasons and suggested support.'),
        ('Analytics', 'Validated predictive model', MISSING, 'Needs historical outcomes, temporal hold-out validation and calibration.'),
        ('Analytics', 'Fairness and bias evaluation', MISSING, 'Subgroup checks required before any predictive use.'),
        ('Analytics', 'Weekly trends and teaching-pace alerts', IMPLEMENTED, 'Calendar-aware; CAT and exam days excluded.'),
        ('Action', 'Intervention recording', IMPLEMENTED, 'Staff record support actions per student.'),
        ('Action', 'Intervention outcome tracking and closure', PARTIAL, 'Status is stored; no screen yet to update or close a case.'),
        ('Action', 'Automatic alerts (email / SMS)', MISSING, 'Alerts are only visible inside the app.'),
        ('Action', 'Student-facing view', MISSING, 'Students cannot see their own indicators.'),
        ('Security & governance', 'Role-based access and audit log', IMPLEMENTED, 'Dean, HOD, lecturer, TA and admin scopes; actions audited.'),
        ('Security & governance', 'CSRF protection', IMPLEMENTED, 'All forms carry a session token.'),
        ('Security & governance', 'HTTPS deployment', IMPLEMENTED if https else MISSING, 'COOKIE_SECURE=1 is set.' if https else 'Runs on plain HTTP; host behind HTTPS before real use.'),
        ('Security & governance', 'Login rate limiting', MISSING, 'Unlimited password attempts.'),
        ('Security & governance', 'Multi-factor authentication', MISSING, ''),
        ('Security & governance', 'Self-service password reset', MISSING, 'Administrator must create accounts.'),
        ('Security & governance', 'Database migrations and tested backups', MISSING, 'Back up sefa.db manually.'),
        ('Security & governance', 'Data protection impact assessment', MISSING, 'Institutional process; required before real student data.'),
        ('Usability', 'Responsive web interface', IMPLEMENTED, 'Works on desktop, tablet and phone browsers.'),
        ('Usability', 'CSV exports', IMPLEMENTED, 'Monitoring, risk and pilot evaluation exports.'),
        ('Usability', 'PDF reports', MISSING, ''),
        ('Usability', 'Kinyarwanda / French interface', MISSING, 'English only.'),
        ('Pilot evaluation', 'Usage analytics', IMPLEMENTED, 'Pages and actions per feature and role; no student identifiers stored.'),
        ('Pilot evaluation', 'Structured user feedback', IMPLEMENTED, 'Ratings, bug reports and feature requests from every role.'),
    ]
    items = [{'category': c, 'capability': n, 'status': s, 'note': note} for c, n, s, note in rows]
    categories = {}
    for item in items:
        bucket = categories.setdefault(item['category'], {'category': item['category'], 'implemented': 0, 'partial': 0, 'not yet': 0, 'points': 0.0, 'total': 0})
        bucket[item['status']] += 1
        bucket['points'] += SCORE[item['status']]
        bucket['total'] += 1
    for bucket in categories.values():
        bucket['readiness_percent'] = round(100 * bucket['points'] / bucket['total'])
    overall = round(100 * sum(SCORE[i['status']] for i in items) / len(items))
    return {'capabilities': items, 'categories': list(categories.values()), 'readiness_percent': overall,
            'note': 'Self-assessed against common university early-alert capabilities; not a certification.'}


def moodle_configured():
    return bool(os.getenv('MOODLE_URL') and os.getenv('MOODLE_TOKEN'))
