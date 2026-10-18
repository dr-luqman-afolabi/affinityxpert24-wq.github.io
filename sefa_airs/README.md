# SEFA-AIRS — Working pilot foundation (v0.1)

A standalone FastAPI web app for user accounts, course offerings, student CSV/XLSX imports, attendance, assessment scores, course-topic coverage, rule-based risk analytics, interventions, and CSV reports. It is **not** a complete or production-certified system.

## Windows setup

1. Install Python 3.11+.
2. In PowerShell, from this folder:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python create_admin.py
   $env:SESSION_SECRET = "replace-with-a-long-random-secret-for-this-session"
   uvicorn app:app --host 127.0.0.1 --port 8000
   ```
3. Open http://127.0.0.1:8000 and log in with the admin credentials you created.
4. Create users, create courses, then upload a CSV/XLSX student roster with `student_no,name,programme` headers.

## Pilot limitations / security caveats

- Uses SQLite by default for local demonstration. Set `DATABASE_URL` to PostgreSQL for a larger deployment; database migrations are not yet implemented.
- Session secret must be persistent between restarts. Set `COOKIE_SECURE=1` when served over HTTPS.
- CSRF protections, login rate limiting, MFA, recovery flows, upload malware scanning, formal approval workflows, granular TA course assignments, curriculum version approval, and deployment hardening are **not yet implemented**.
- Uploaded curriculum documents are text-extracted and stored; no Claude/OpenAI API calls are currently made.
- Risk scoring is transparent rule-based logic, **not predictive AI**. It uses only attendance and available assessment scores, not assignment completion or LMS engagement as separate inputs. It is illustrative and unvalidated.
- Late attendance is treated as not present in the pilot score; revise policy before real use.
- TAs currently have programme-wide course access rather than per-course assignments; narrow this before real use.
- Do not enter real student information until university authorization, security testing, and applicable data-protection reviews are complete.
- ERP integration, PDF reports, and AI model integration are future phases, not implemented in this archive.

## Version 0.2 additions (development build)

- CSRF tokens added to HTML forms; login creates a session token.
- TA access is restricted to explicitly assigned course offerings. After creating a TA and a course, an admin/dean/HOD must assign the TA using `POST /ta-assignments` (fields `ta_id`, `course_id`, `csrf_token`). A visual assignment form is not yet provided.
- `GET /api/courses/{id}/coverage` returns planned/completed hours and coverage percentage.
- `GET /api/courses/{id}/ai-brief` returns an aggregate-only offline summary when no API key is set; when `ANTHROPIC_API_KEY` is set, it calls Claude. Optionally set `ANTHROPIC_MODEL` to a currently supported model identifier. AI calls incur provider charges. The AI summary endpoint has no application-level per-user quota or caching yet.
- Stronger checks for numeric input and malformed dates.

**Important:** This build has passed Python syntax compilation only. The current environment did not have all runtime dependencies available for an end-to-end test. Do not use it with real student data or expose it to the internet. CSRF is not a substitute for login throttling, MFA, audit review, robust uploads, backup restoration tests, and an independent security assessment. It still uses server-rendered HTML rather than the planned React frontend.

## Version 0.3 additions (October 2026)
- Redesigned responsive academic dashboard with course enrolment, high-risk counts, missing-data counts, and syllabus coverage bars.
- Curriculum archive viewer, programme-specific upload controls, and teaching assistant assignment form.
- `/api/dashboard` provides authorized, aggregated course analytics.
- Added programme validation for course creation and lecturer assignment.
- Restricts grade entry, topic editing, and interventions to academic staff (not TAs or technical administrators).
- CSS assets served from `/static`.

### Limitations before real-student deployment
This is an **unverified pilot**, not a production-ready university system. Python syntax compilation succeeded, but full end-to-end tests were not run in this environment because required runtime dependencies are absent. In particular, user creation, password reset, rate limiting, stronger session security, enrollment approval, database migrations, multi-programme course handling, file scanning, fine-grained permissions, curriculum extraction review, and formal data-protection approval require further work. The dashboard's high-risk counts are course enrolments, not distinct students. AI model outputs are not validated forecasts.


## v0.4 Modular sessions, intakes and weekly progress
- Each new course offering has **morning / evening / weekend** session, an **intake code**, a **module**, start/end dates, and a teaching-week count. Use distinct intake codes for the three annual intakes (actual dates are institution-defined).
- Course rosters are separate per offering; students may appear in multiple offerings.
- Bulk attendance: `POST /courses/{id}/attendance/import`, CSV/XLSX columns `student_no,session_date,status`. Status is `present`, `absent`, or `late`. Invalid rows reject the whole file; valid rows update existing attendance for the same date.
- Curriculum uploads now support CSV/XLSX in addition to TXT/DOCX/PDF. This stores extracted content for review; it does **not** automatically create approved course catalogue records.
- Weekly coverage import: `POST /courses/{id}/weekly/import`, columns `week_no,planned_topic,planned_hours,delivered_hours,delivery_notes`. Updates matching topic/week. Lecturer, HOD and Dean can upload; TAs can view.
- Weekly coverage reports: `GET /api/courses/{id}/weekly-coverage` and `GET /api/weekly-coverage?session_type=weekend&intake=2026-01&module=Module%201`. The denominator is all *uploaded planned hours*; upload the complete teaching plan first to avoid misleading percentages.
- `sample_attendance.csv`, `sample_weekly_coverage.csv`, `sample_curriculum.csv` demonstrate required columns.

### Known limitations
- v0.4 is a development prototype, not a production-ready student records system. It has not been penetration-tested.
- The three annual intakes are **configurable labels**, not hardcoded institutional dates. Academic calendars and module schedules need UoK confirmation.
- Week-by-week coverage is based on lecturer-reported delivered hours, not independent verification of teaching quality.
- No automatic background Excel ingestion or scheduled synchronization: staff upload files through the web interface.
- The existing `courses` table stores a composite offering identifier in its `code` field; a later migration should separate canonical course code and offering ID.
- Existing database schema changes should be tested on a backed-up copy before using live data.

## v0.5 provisional modular calendar
The standalone scheduling library `modular_calendar.py` and authenticated endpoint
`GET /api/modular-calendar/preview?start_date=2026-11-02&session_type=morning&credits=10`
preview dated teaching/CAT/exam slots. `break_minutes` can deduct scheduled breaks
from teaching hours. Default teaching weekdays are Mon–Fri for morning/evening,
Sat–Sun for weekend; these are configurable in Python but not yet in the UI.
Assumption pending SEFA confirmation: **10 teaching days before CAT + 1 CAT day
+ 5 teaching days after CAT + 1 exam day = 17 days**; evening has one extra
teaching day before CAT (18 total days). The same teaching-day sequence is
provisionally used for 10- and 15-credit courses and weekends. The system does
NOT infer credit hours from clock hours, and excludes CAT/exam hours from teaching
coverage. Holidays, make-up classes, timetable conflicts, and week-by-week
actual delivery are not yet incorporated into this calendar preview. This is
not a production-ready scheduling engine.

## Version 0.6 — Flexible modular scheduling

Confirmed default: 10 teaching days, CAT, 5 teaching days, exam = 17 scheduled days; evening adds one teaching day = 18. Both 10- and 15-credit courses use this sequence by default, including weekend courses. Default time windows: morning 08:30–11:30 (10 credits), 08:30–12:00 (15); evening 18:00–21:00; weekend 08:30–14:00 (10), 08:30–16:00 (15). Credit values do **not** imply clock-hour totals.

The authenticated `/api/modular-calendar/preview` endpoint accepts configurable `before_cat`, `after_cat`, `evening_extra_days`, `extra_days_before_cat` (place evening extra days before/after CAT), `start_time`, `end_time`, `break_minutes`, `weekdays` (comma-separated Monday=0), `excluded_dates` (comma-separated YYYY-MM-DD), and `coverage_target` (default 85). Dates skip holidays/exclusions. A generated plan does not imply that teaching actually happened; verification and topic-based coverage still need integration into the course progress workflow. The API is a preview and does not yet persist approved timetable changes.


## Version 0.7: curriculum documents supplied by SEFA

- `curriculum_catalog.py`: conservative DOCX programme module table extractor.
- `curriculum_review/finance_2023_review.csv`: 38 candidate modules from Finance revision dated August 2025.
- `curriculum_review/accounting_2023_review.csv`: 40 candidate modules from Accounting revision dated August 2025.
- `curriculum_review/economics_2023_review.csv`: 20 candidate modules from the Economics 2023 document.
- `curriculum_review/economics_2017_review.csv`: empty review file; the 2017 document requires manual extraction/review.
- `GET /api/curriculum-catalogue?programme=Finance` (or Accounting/Economics): role-protected review API.
- Credits deliberately blank until a reviewer verifies the source. Academic years, programme versions and approval status must be reviewed before use for scheduling.
- This release does not automatically approve curricula, map modules to teaching sessions, or overwrite current course offerings.
- Original source documents retained in `curriculum_sources/` for traceability.

## Version 0.8: Approved 2023 curriculum and floated modules only
- Only the **2023** curriculum catalogues are available to the application; the 2017 Economics review CSV is removed.
- A course must first be explicitly **floated** for a specific academic year, intake, session (morning/evening/weekend), and module block by Dean/HOD/admin using `POST /api/float-module`.
- `GET /api/floated-modules` provides the selectable list for that intake/session/block; do **not** show the entire curriculum as selectable courses.
- Course creation `POST /courses` now rejects any code/title absent from the approved 2023 curriculum and any course not already floated for the matching intake/session/block.
- Existing course offerings and student data are not automatically migrated. Existing records created before v0.8 require manual reconciliation; no destructive database migration is included.
- The 2023 catalogue's blank credit fields remain blank. Verify credits from the signed documents rather than inferring them. This is an API-first workflow; the dropdown UI remains to be connected.

## Version 0.9: floated-module selection interface

The Academic overview now includes an **Authorize floating** form for Dean/HOD/admin accounts. It loads module codes and titles from the approved 2023 curriculum catalogue. The **Create course offering** form dynamically filters selectable modules by programme, academic year, intake, session and module block. The approved module title is populated automatically and checked again by the backend. Lecturers and TAs cannot float modules.

Workflow: (1) Create user accounts; (2) choose programme and approve a module float for a particular cohort; (3) use the same academic year, intake, session and module block in Create course offering; (4) select the floated module; (5) assign a lecturer and dates; (6) open the created course to upload student rosters, attendance and teaching progress.

The dynamic selection requires a working backend and signed-in session. This remains a development pilot, not a production-certified ERP integration. Credit fields absent from the extracted source catalogue require manual verification; the app does not invent credits. Current offering identifiers are shortened to 40 characters, so administrators should use concise intake and module-block identifiers until the database model is upgraded. Existing SQLite databases should be backed up before applying code updates.


## Version 0.10: TA student profile and attendance spreadsheet uploads
Assigned TAs may upload CSV/XLSX attendance lists with `student_no,session_date,status` (present/absent/late) and student rosters with required `student_no,name,programme` plus optional `email,phone,intake,session`. The roster import validates all rows, blocks duplicate student numbers and conflicting existing profiles, and creates one student identity with course-specific enrolments. Student profiles are stored separately in `student_profiles`; no new sensitive profile fields should be introduced without university approval. Uploaded spreadsheets are not retained. Use `sample_student_profiles.csv` and `sample_attendance.csv` as templates. This is a pilot and still needs comprehensive authorization/security and deployment tests.

## Version 0.11: TA spreadsheet preview and confirmation

For each assigned floated course, TAs can upload `.csv` or `.xlsx` attendance and student-profile spreadsheets. The course page now opens a **preview** rather than saving immediately. It shows the first 30 records and validation errors, with a confirm button only for a valid import. Preview data is stored temporarily in the database, scoped to the uploader and course, and expires after 30 minutes. Confirmation revalidates records and commits all changes in one transaction; invalid files make no changes. Imports are audited. Uploaded profile details are not sent to an AI provider by this workflow.

**Known limitations:** The preview stores student details in the application's database until confirmation; expired previews need a periodic cleanup job for data minimization. Imports currently allow replacing an existing attendance status on confirmation, so a review/approval policy for attendance corrections is advisable. Existing legacy one-step import endpoints remain for compatibility and should be disabled before institutional production rollout. The entire pilot needs authentication/security review and runtime integration testing before real student data is used.


## Version 0.12 — calendar-aware attendance and weekly monitoring

- `GET /api/courses/{course_id}/academic-monitor?credits=10` returns teaching-day register completeness, weekly aggregates, observed attendance rate, syllabus hours coverage, and alerts. Optional `as_of=YYYY-MM-DD`, `break_minutes`, `weekdays` and `excluded_dates` customize the calendar.
- `GET /api/academic-monitor?credits=10&session_type=morning&intake=...` provides filtered multi-course reports. **Warning:** credits apply to every course in that report until a per-offering credit field is implemented. Do not combine mixed-credit courses in one report.
- The course page has a simple report form. Output is JSON; a graphical chart interface is not yet built.
- Teaching calendar uses the existing 17-day day/weekend and 18-day evening defaults, excluding CAT/exam days from teaching attendance and coverage pacing.
- Missing registers and incomplete student entries are never silently classified as student absences. Attendance rates use recorded entries as denominator and expose data completeness separately.
- Coverage hours are lecturer-reported, not independently verified. Calendar pace alerts are indicative and should not be interpreted as proof of poor teaching.
- Pilot still requires full authentication, security, and deployment testing; not suitable for live student data without university authorization.


## Version 0.13 — graphical monitoring

After signing in, open `/monitor` to view a role-scoped, filtered dashboard for programme, session, intake, and module block. It shows course-level coverage bars with an 85% final target marker, recorded attendance rates, and CSV export at `/monitor.csv`. No credit hours are inferred from the catalogue. Attendance figures include only recorded statuses and do not represent register completeness. The view does not yet include a weekly time-series graph; the existing `/api/courses/{id}/academic-monitor?credits=10` endpoint provides week-by-week results after a verified credit value is supplied.

This remains a development pilot, not a production-certified system.


## Version 0.14 — Verified offering credits and weekly trend reporting

- Authorized Dean/HOD/admin users can POST a CSRF-protected `credits=10` or `credits=15` to `/api/courses/{id}/credits`. The verified value is persisted in a separate `offering_credit_config` table, avoiding alterations to existing SQLite columns. Verify against the signed 2023 curriculum.
- `/api/courses/{id}/academic-monitor` now uses verified credits and rejects conflicting query parameters. `/api/academic-monitor` omits unconfigured courses rather than assuming a credit value.
- `/api/courses/{id}/weekly-trends` returns ISO-week attendance-register completeness, observed attendance among recorded entries, planned teaching hours, and delivered topic coverage. Course pages render these figures.
- Teaching-plan week numbers are treated as ordinal calendar weeks; verify that course plans follow this convention. Calendar overrides are not yet stored per offering, and the trend endpoint uses default schedule rules.
- No real student data should be used until full authentication, integration, data protection, and end-to-end security testing are completed.

## Version 0.15 — verified teaching-plan workflow

- `TeachingPlanItem` persists week, topic, planned hours, lecturer-reported delivered hours, TA verification, and HOD/Dean approval status.
- Lecturers/HODs/Dean can upload a complete draft plan using CSV/XLSX (`week_no,planned_topic,planned_hours`). An existing plan with delivery evidence is locked against bulk replacement.
- Assigned lecturer submits each topic's actual delivered hours through `POST /api/teaching-plan/{item_id}/report`.
- Assigned TA verifies/returns the submitted report using `POST /api/teaching-plan/{item_id}/ta-review`.
- HOD or Dean approves/returns TA-verified reports using `POST /api/teaching-plan/{item_id}/hod-review`.
- `GET /api/courses/{course_id}/teaching-plan?current_week=2` returns the plan, verified coverage, expected scheduled coverage, and overdue/unapproved alerts.
- The course page has a plan upload and read-only status panel. Report/review/approve forms are API-only in this version, and an interactive approval UI remains outstanding.
- The existing legacy `WeeklyCoverage` upload and monitoring routes remain separate; their unverified hours must NOT be interpreted as HOD-approved hours. Reconciliation of the two pathways is still required.
- SQLAlchemy creates the new table for fresh databases. Existing database changes need a reviewed migration/backup process; no formal Alembic migration is included.
- The `current_week` parameter is entered manually, not automatically derived from approved holiday-adjusted timetables. Automatic reminders/background jobs are not implemented; alerts are returned when the endpoint is queried.
- This is a development build; do not use real student data before security, privacy and end-to-end review.


## Version 0.16 — teaching plan action screens

- Lecturer can submit delivered teaching hours and notes from the course page.
- Assigned TA can verify or return submitted teaching reports.
- Authorized HOD/Dean can approve or return TA-verified reports.
- Forms use same-origin POST with CSRF tokens and display server errors.
- `/api/dean/verified-coverage` provides programme/session/intake filters, verified coverage, and pending TA/HOD counts.
- **Important:** Full browser and integration testing is pending; do not use with real student data before security review.


## Version 0.17: Explainable academic-support intelligence

- Open `/ai-risk` after logging in, select an authorized course, and review the student-support indicators.
- API: `GET /api/courses/{course_id}/ai-risk`; CSV: `GET /api/courses/{course_id}/ai-risk.csv`. Dean/HOD aggregate endpoint: `GET /api/dean/ai-risk-summary`.
- The engine is deterministic, not a trained prediction model. It uses recorded attendance (late counts as attended), valid grades, and open interventions. At least three attendance entries are required for attendance to contribute to risk. Missing registers never count as absences. A single available evidence source receives a provisional risk band.
- Existing v0.16 risk routes remain for compatibility; use the v0.17 AI-risk routes for improved explanations.
- The AI-risk dashboard does not send individual student records to external LLM services. The existing `/api/courses/{course_id}/ai-brief` route sends aggregate data to Anthropic only when configured.
- Academic staff must review all suggested interventions. Do not use risk bands for automated penalties, admissions, grading, exclusion, or other consequential decisions.
- **Production gaps:** historical-outcome training, predictive accuracy and fairness validation, privacy impact assessment, authentication/session hardening, authorization testing, record retention and deletion policy, access audit review, and independent security review.


## Version 0.18: AI risk validation and data-quality monitoring

- `/api/courses/{course_id}/ai-risk-quality` reports evidence completeness for an authorized academic user.
- `POST /api/dean/ai-risk-validation` allows Dean/HOD to compare the current explainable triage bands against **explicitly supplied historical outcome labels**. JSON body: `{"threshold":"high","records":[{"course_id":1,"student_no":"EXAMPLE","adverse_outcome":true}]}`. Requires the signed-in user's `X-CSRF-Token` session token. The request does not persist labels. Duplicate or unenrolled student labels are rejected.
- A minimum of 30 scored, labeled records is required to show retrospective precision/recall/specificity; small samples return suppression notice. This minimum is a display safeguard, **not** a claim of statistical sufficiency.
- Historical labels should be appropriately authorized and collected only with institutional privacy approval. Do not use validation endpoints with live student records until a DPIA, consent/lawful-basis review, and role/security assessment are complete.
- The rule-based score is **not a trained ML model or validated dropout probability**. A complete predictive system still requires cohort definition, longitudinal outcomes, temporal holdout validation, subgroup fairness checks, calibration, monitoring and formal institutional approval.
- The current validation endpoint is exploratory: it compares labels against *current* records and is **not a genuine historical out-of-sample test**. Do not present the reported metrics as predictive performance.
- No external LLM is called to process student records.

## v0.19 safety corrections and outstanding blockers

- Both legacy course-page scores and AI dashboard use `explainable_rules_v2`.
- Assessment evidence is calculated as earned points divided by available points; this **does not implement the approved CAT/quiz/exam component weighting**, which requires a separately approved configuration.
- When a verified offering credit configuration and schedule exist, risk attendance excludes CAT, exam, unscheduled dates and duplicate dates. Without verified calendar information, recorded entries remain provisional and require reconciliation.
- The historical-validation POST endpoint deliberately returns HTTP 409 until dated, pre-outcome feature snapshots are available. Previous descriptive validation results must not be described as predictive validation.
- The course-code uniqueness constraint and course-code truncation still need a versioned, tested database migration. Do not alter the existing database schema by editing the ORM constraint alone.
- Authentication rate limiting, secure password recovery, migration tooling, integration tests, security review, and fairness evaluation remain required for production.
- Run `pip install -r requirements.txt`, then `PYTHONPATH=. pytest -q` from this folder. Production student records must not be imported before institutional security and data protection approvals.
