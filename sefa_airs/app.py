"""SEFA-AIRS standalone pilot. Not production certified."""
import os, csv, io, json, secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, Text, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import hmac
from passlib.context import CryptContext

ROOT=Path(__file__).resolve().parent
DATABASE_URL=os.getenv('DATABASE_URL',f'sqlite:///{ROOT / "sefa.db"}')
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal=sessionmaker(bind=engine)
Base=declarative_base()
crypt=CryptContext(schemes=['bcrypt'],deprecated='auto')
app=FastAPI(title='SEFA-AIRS Pilot',version='0.19.0')
secret=os.getenv('SESSION_SECRET')
if not secret:
    secret=secrets.token_hex(32)
app.add_middleware(SessionMiddleware,secret_key=secret,https_only=os.getenv('COOKIE_SECURE','0')=='1',same_site='lax')
templates=Jinja2Templates(directory=str(ROOT/'templates'))
app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')

class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True); username=Column(String(100),unique=True,nullable=False); password_hash=Column(String(255),nullable=False)
    role=Column(String(20),nullable=False); programme=Column(String(60),nullable=True)
class TAAssignment(Base):
    __tablename__='ta_assignments'
    id=Column(Integer,primary_key=True)
    ta_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    course_id=Column(Integer,ForeignKey('courses.id'),nullable=False)
    __table_args__=(UniqueConstraint('ta_id','course_id'),)

class Student(Base):
    __tablename__='students'
    id=Column(Integer,primary_key=True); student_no=Column(String(60),unique=True,nullable=False); name=Column(String(200),nullable=False); programme=Column(String(60),nullable=False)
class StudentProfile(Base):
    __tablename__='student_profiles'
    id=Column(Integer,primary_key=True)
    student_id=Column(Integer,ForeignKey('students.id'),unique=True,nullable=False)
    email=Column(String(200),nullable=True)
    phone=Column(String(60),nullable=True)
    intake=Column(String(40),nullable=True)
    session=Column(String(12),nullable=True)
    updated_by=Column(Integer,ForeignKey('users.id'))
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class Course(Base):
    __tablename__='courses'
    id=Column(Integer,primary_key=True); code=Column(String(40),nullable=False); title=Column(String(200),nullable=False)
    programme=Column(String(60),nullable=False); academic_year=Column(String(30),nullable=False); lecturer_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    __table_args__=(UniqueConstraint('code','academic_year',name='unique_course_offering'),)
class FloatedModule(Base):
    __tablename__='floated_modules'
    id=Column(Integer,primary_key=True)
    programme=Column(String(60),nullable=False)
    module_code=Column(String(40),nullable=False)
    academic_year=Column(String(30),nullable=False)
    intake=Column(String(40),nullable=False)
    session=Column(String(12),nullable=False)
    module_block=Column(String(60),nullable=False)
    status=Column(String(20),nullable=False,default='floated')
    created_by=Column(Integer,ForeignKey('users.id'))
    __table_args__=(UniqueConstraint('programme','module_code','academic_year','intake','session','module_block'),)

class OfferingSchedule(Base):
    __tablename__='offering_schedules'
    id=Column(Integer,primary_key=True)
    course_id=Column(Integer,ForeignKey('courses.id'),unique=True,nullable=False)
    session=Column(String(12),nullable=False)  # morning, evening, weekend
    intake=Column(String(40),nullable=False)  # intake code, e.g. 2026-01
    module=Column(String(60),nullable=False)
    start_date=Column(String(10),nullable=False)
    end_date=Column(String(10),nullable=False)
    weeks=Column(Integer,nullable=False)
class OfferingCreditConfig(Base):
    __tablename__='offering_credit_config'
    course_id=Column(Integer,ForeignKey('courses.id'),primary_key=True)
    credits=Column(Integer,nullable=False)
    verified_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    verified_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class WeeklyCoverage(Base):
    __tablename__='weekly_coverage'
    id=Column(Integer,primary_key=True)
    course_id=Column(Integer,ForeignKey('courses.id'),nullable=False)
    week_no=Column(Integer,nullable=False)
    planned_topic=Column(String(300),nullable=False)
    planned_hours=Column(Float,nullable=False)
    delivered_hours=Column(Float,default=0,nullable=False)
    delivery_notes=Column(Text,default='')
    updated_by=Column(Integer,ForeignKey('users.id'))
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    __table_args__=(UniqueConstraint('course_id','week_no','planned_topic'),)
class TeachingPlanItem(Base):
    __tablename__='teaching_plan_items'
    id=Column(Integer,primary_key=True)
    course_id=Column(Integer,ForeignKey('courses.id'),nullable=False)
    week_no=Column(Integer,nullable=False)
    planned_topic=Column(String(300),nullable=False)
    planned_hours=Column(Float,nullable=False)
    delivered_hours=Column(Float,nullable=True)
    lecturer_notes=Column(Text,default='')
    ta_notes=Column(Text,default='')
    hod_notes=Column(Text,default='')
    status=Column(String(20),nullable=False,default='planned')
    updated_by=Column(Integer,ForeignKey('users.id'))
    reviewed_by=Column(Integer,ForeignKey('users.id'))
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    __table_args__=(UniqueConstraint('course_id','week_no','planned_topic',name='unique_teaching_plan_topic'),)

class Enrollment(Base):
    __tablename__='enrollments'
    id=Column(Integer,primary_key=True); student_id=Column(Integer,ForeignKey('students.id')); course_id=Column(Integer,ForeignKey('courses.id'))
    __table_args__=(UniqueConstraint('student_id','course_id'),)
class Attendance(Base):
    __tablename__='attendance'
    id=Column(Integer,primary_key=True); student_id=Column(Integer,ForeignKey('students.id')); course_id=Column(Integer,ForeignKey('courses.id'))
    session_date=Column(String(10)); status=Column(String(10)); recorded_by=Column(Integer,ForeignKey('users.id'))
    __table_args__=(UniqueConstraint('student_id','course_id','session_date'),)
class Assessment(Base):
    __tablename__='assessments'
    id=Column(Integer,primary_key=True); student_id=Column(Integer,ForeignKey('students.id')); course_id=Column(Integer,ForeignKey('courses.id'))
    kind=Column(String(30)); title=Column(String(100)); score=Column(Float); max_score=Column(Float)
    __table_args__=(UniqueConstraint('student_id','course_id','kind','title'),)
class Curriculum(Base):
    __tablename__='curricula'
    id=Column(Integer,primary_key=True); programme=Column(String(60)); version=Column(String(60)); filename=Column(String(200)); content=Column(Text); uploaded_by=Column(Integer,ForeignKey('users.id')); uploaded_at=Column(DateTime,default=datetime.utcnow)
class Topic(Base):
    __tablename__='topics'
    id=Column(Integer,primary_key=True); course_id=Column(Integer,ForeignKey('courses.id')); title=Column(String(200)); planned_hours=Column(Float,default=1); completed_hours=Column(Float,default=0)
class Intervention(Base):
    __tablename__='interventions'
    id=Column(Integer,primary_key=True); student_id=Column(Integer,ForeignKey('students.id')); course_id=Column(Integer,ForeignKey('courses.id'))
    note=Column(Text); status=Column(String(30),default='open'); created_by=Column(Integer,ForeignKey('users.id')); created_at=Column(DateTime,default=datetime.utcnow)
class PendingImport(Base):
    __tablename__='pending_imports'
    id=Column(String(64),primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    course_id=Column(Integer,ForeignKey('courses.id'),nullable=False)
    import_type=Column(String(20),nullable=False)
    payload=Column(Text,nullable=False)
    filename=Column(String(200),nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class Audit(Base):
    __tablename__='audit'
    id=Column(Integer,primary_key=True); user_id=Column(Integer); action=Column(String(100)); detail=Column(Text); created_at=Column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)

def db():
    session=SessionLocal()
    try: yield session
    finally: session.close()

def actor(request:Request,s:Session=Depends(db)):
    uid=request.session.get('uid')
    u=s.get(User,uid) if uid else None
    if not u: raise HTTPException(401,'Please sign in')
    return u

def allowed(u,course):
    if u.role in ('admin','dean'): return True
    if u.role=='hod': return u.programme==course.programme
    if u.role=='lecturer': return course.lecturer_id==u.id
    if u.role=='ta':
        with SessionLocal() as session:
            return session.query(TAAssignment).filter_by(ta_id=u.id,course_id=course.id).first() is not None
    return False

def require_course(s,u,course_id):
    c=s.get(Course,course_id)
    if not c or not allowed(u,c): raise HTTPException(403,'Course access denied')
    return c

def audit(s,u,action,detail=''):
    s.add(Audit(user_id=u.id,action=action,detail=detail))

def view(request,s,u,message=''):
    courses=[c for c in s.query(Course).order_by(Course.code).all() if allowed(u,c)]
    students=s.query(Student).count() if u.role in ('dean','admin') else s.query(Student).filter(Student.programme==u.programme).count()
    summaries=[]
    for c in courses:
        people=roster(s,c.id)
        risks=[score(s,c.id,st.id) for st in people]
        topics=s.query(Topic).filter_by(course_id=c.id).all()
        planned=sum(t.planned_hours for t in topics)
        completed=sum(min(t.completed_hours,t.planned_hours) for t in topics)
        summaries.append({'course':c,'count':len(people),'high':sum(r['label'] in ('high','critical') for r in risks),'unknown':sum(r['risk'] is None for r in risks),'coverage':round(100*completed/planned,1) if planned else None})
    totals={'courses':len(courses),'enrollments':sum(x['count'] for x in summaries),'high':sum(x['high'] for x in summaries),'unknown':sum(x['unknown'] for x in summaries)}
    tas=s.query(User).filter_by(role='ta').order_by(User.username).all() if u.role in ('admin','dean','hod') else []
    lecturers=s.query(User).filter_by(role='lecturer').order_by(User.username).all() if u.role in ('admin','dean','hod') else []
    curricula=s.query(Curriculum).order_by(Curriculum.uploaded_at.desc()).all() if u.role in ('admin','dean') else s.query(Curriculum).filter_by(programme=u.programme).order_by(Curriculum.uploaded_at.desc()).all()
    return templates.TemplateResponse(request,'index.html',{'user':u,'courses':courses,'students':students,'summaries':summaries,'totals':totals,'tas':tas,'lecturers':lecturers,'curricula':curricula,'message':message,'csrf':request.session.get('csrf','')})

@app.get('/',response_class=HTMLResponse)
def home(request:Request,s:Session=Depends(db)):
    uid=request.session.get('uid'); u=s.get(User,uid) if uid else None
    if not u:
        request.session.setdefault('csrf',secrets.token_urlsafe(32))
        return templates.TemplateResponse(request,'login.html',{'error':'','csrf':request.session['csrf']})
    return view(request,s,u)

def check_csrf(request:Request,csrf_token:str=Form(...)):
    expected=request.session.get('csrf','')
    if not expected or not hmac.compare_digest(expected,csrf_token):
        raise HTTPException(403,'Invalid CSRF token')

@app.post('/login')
def login(request:Request,username:str=Form(...),password:str=Form(...),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    u=s.query(User).filter(User.username==username).first()
    if not u or not crypt.verify(password,u.password_hash):
        return templates.TemplateResponse(request,'login.html',{'error':'Invalid credentials','csrf':request.session.get('csrf','')},status_code=401)
    request.session.clear(); request.session['uid']=u.id; request.session['csrf']=secrets.token_urlsafe(32)
    return RedirectResponse('/',303)
@app.post('/logout')
def logout(request:Request,_csrf:None=Depends(check_csrf)):
    request.session.clear();return RedirectResponse('/',303)

@app.post('/users')
def add_user(username:str=Form(...),password:str=Form(...),role:str=Form(...),programme:str=Form(''),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    if u.role!='admin':raise HTTPException(403)
    if role not in ('admin','dean','hod','lecturer','ta'):raise HTTPException(400)
    if len(password)<12:raise HTTPException(400,'Password must have at least 12 characters')
    if s.query(User).filter(User.username==username).first():raise HTTPException(409,'Username exists')
    s.add(User(username=username,password_hash=crypt.hash(password),role=role,programme=programme or None));audit(s,u,'create_user',username);s.commit()
    return RedirectResponse('/',303)

@app.post('/ta-assignments')
def assign_ta(ta_id:int=Form(...),course_id:int=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    if u.role not in ('admin','dean','hod'):raise HTTPException(403)
    course=s.get(Course,course_id);ta=s.get(User,ta_id)
    if not course or not ta or ta.role!='ta' or ta.programme!=course.programme:raise HTTPException(400,'Invalid TA or course')
    if u.role=='hod' and u.programme!=course.programme:raise HTTPException(403)
    if not s.query(TAAssignment).filter_by(ta_id=ta_id,course_id=course_id).first():
        s.add(TAAssignment(ta_id=ta_id,course_id=course_id))
        audit(s,u,'assign_ta',f'{ta_id}:{course_id}');s.commit()
    return RedirectResponse('/',303)

@app.post('/courses')
def add_course(code:str=Form(...),title:str=Form(...),programme:str=Form(...),academic_year:str=Form(...),session_type:str=Form(...),intake:str=Form(...),module:str=Form(...),start_date:str=Form(...),end_date:str=Form(...),weeks:int=Form(...),lecturer_id:Optional[int]=Form(None),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    if u.role not in ('admin','dean','hod'):raise HTTPException(403)
    if programme not in ('Economics','Finance','Accounting'):raise HTTPException(400,'Invalid programme')
    if u.role=='hod' and u.programme!=programme:raise HTTPException(403)
    if lecturer_id is not None:
        lecturer=s.get(User,lecturer_id)
        if not lecturer or lecturer.role!='lecturer' or lecturer.programme!=programme:raise HTTPException(400,'Lecturer must belong to programme')
    if session_type not in ('morning','evening','weekend') or not 1<=weeks<=52 or not intake.strip() or not module.strip():raise HTTPException(400,'Invalid session/intake/module/weeks')
    try:
        if date.fromisoformat(start_date)>date.fromisoformat(end_date):raise ValueError()
    except ValueError:raise HTTPException(400,'Invalid module dates')
    # Only modules explicitly floated from the approved 2023 programme curriculum may be offered.
    from floated_modules import validate_float
    try: approved=validate_float(ROOT,programme,code,title)
    except ValueError as e:raise HTTPException(400,str(e))
    floated=s.query(FloatedModule).filter_by(programme=programme,module_code=approved['module_code'],academic_year=academic_year,intake=intake.strip(),session=session_type,module_block=module.strip(),status='floated').first()
    if not floated:raise HTTPException(400,'Module is not floated for this academic year, intake, session and module block')
    # A course code can occur in multiple sessions/intakes. Internal offering code is unique per cohort.
    internal_code=f'{code.strip()}-{intake.strip()}-{session_type}-{module.strip()}'
    c=Course(code=internal_code[:40],title=title,programme=programme,academic_year=academic_year,lecturer_id=lecturer_id)
    s.add(c);s.flush()
    s.add(OfferingSchedule(course_id=c.id,session=session_type,intake=intake.strip(),module=module.strip(),start_date=start_date,end_date=end_date,weeks=weeks))
    audit(s,u,'create_course',internal_code);s.commit();return RedirectResponse('/',303)

@app.post('/courses/{course_id}/students')
async def upload_students(course_id:int,file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    c=require_course(s,u,course_id)
    if u.role not in ('ta','lecturer','hod','dean','admin'):raise HTTPException(403)
    rows=parse_tabular_upload(file.filename or '',await file.read())
    try:
        checked=validate_roster_rows(rows,c.programme)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    # Validate the entire file and existing identities before writing any records.
    for record in checked:
        existing=s.query(Student).filter_by(student_no=record['student_no']).first()
        if existing and (existing.name!=record['name'] or existing.programme!=record['programme']):
            raise HTTPException(422,f"Conflicting existing student record: {record['student_no']}")
        if existing:
            profile=s.query(StudentProfile).filter_by(student_id=existing.id).first()
            if profile:
                for field in ('email','phone','intake','session'):
                    if record[field] and getattr(profile,field) and record[field]!=getattr(profile,field):
                        raise HTTPException(422,f"Profile conflict for {record['student_no']}, field {field}; request an authorized correction")
    try:
        for record in checked:
            student=s.query(Student).filter_by(student_no=record['student_no']).first()
            if student is None:
                student=Student(student_no=record['student_no'],name=record['name'],programme=record['programme'])
                s.add(student);s.flush()
            if not s.query(Enrollment).filter_by(student_id=student.id,course_id=c.id).first():
                s.add(Enrollment(student_id=student.id,course_id=c.id))
            if any(record[f] for f in ('email','phone','intake','session')):
                profile=s.query(StudentProfile).filter_by(student_id=student.id).first()
                if profile is None:
                    profile=StudentProfile(student_id=student.id);s.add(profile)
                for field in ('email','phone','intake','session'):
                    if record[field]:setattr(profile,field,record[field])
                profile.updated_by=u.id
        audit(s,u,'roster_profile_import',f'{c.id}: {len(checked)} records');s.commit()
    except Exception:
        s.rollback();raise
    return RedirectResponse(f'/courses/{course_id}',303)

def validate_roster_rows(rows,programme):
    if not rows or not {'student_no','name','programme'}.issubset(rows[0]):
        raise ValueError('Required columns: student_no,name,programme')
    if len(rows)>1000:raise ValueError('Maximum 1000 student rows per file')
    valid=[];seen=set();errors=[]
    for rownum,row in enumerate(rows,2):
        record={k:str(row.get(k) or '').strip() for k in ('student_no','name','programme','email','phone','intake','session')}
        if not record['student_no'] or not record['name'] or record['programme']!=programme:
            errors.append(f'Row {rownum}: missing ID/name or programme mismatch')
        if record['student_no'] in seen:errors.append(f'Row {rownum}: duplicate student number')
        seen.add(record['student_no'])
        if record['email'] and ('@' not in record['email'] or len(record['email'])>200):
            errors.append(f'Row {rownum}: invalid email')
        if record['session'] and record['session'].lower() not in ('morning','evening','weekend'):
            errors.append(f'Row {rownum}: session must be morning/evening/weekend')
        if record['session']:record['session']=record['session'].lower()
        if any(len(record[k])>limit for k,limit in (('student_no',60),('name',200),('phone',60),('intake',40))):
            errors.append(f'Row {rownum}: field too long')
        valid.append(record)
    if errors:raise ValueError('Upload rejected; no records saved. '+'; '.join(errors[:20]))
    return valid

def roster(s,course_id):
    return s.query(Student).join(Enrollment,Enrollment.student_id==Student.id).filter(Enrollment.course_id==course_id).order_by(Student.student_no).all()

def score(s,course_id,student_id):
    """Legacy course view uses the same audited support model as the AI dashboard."""
    result=student_intelligence(s,course_id,student_id)
    return {'attendance':result['attendance_percent'],'assessment':result['assessment_percent'],
            'risk':result['risk_index'],'label':result['risk_band']}

@app.get('/courses/{course_id}',response_class=HTMLResponse)
def course_page(course_id:int,request:Request,u:User=Depends(actor),s:Session=Depends(db)):
    c=require_course(s,u,course_id);people=[{'student':st,'stats':score(s,c.id,st.id)} for st in roster(s,c.id)]
    topics=s.query(Topic).filter_by(course_id=c.id).all()
    planned=sum(t.planned_hours for t in topics);completed=sum(min(t.completed_hours,t.planned_hours) for t in topics)
    return templates.TemplateResponse(request,'course.html',{'user':u,'course':c,'people':people,'topics':topics,'coverage':round(completed/planned*100,1) if planned else None,'weekly':week_report(s,c.id),'schedule':s.query(OfferingSchedule).filter_by(course_id=c.id).first(),'csrf':request.session.get('csrf','')})

@app.post('/courses/{course_id}/attendance')
def record_attendance(course_id:int,student_id:int=Form(...),session_date:str=Form(...),status:str=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    if status not in ('present','absent','late'):raise HTTPException(400)
    try: date.fromisoformat(session_date)
    except ValueError: raise HTTPException(400,'Invalid date')
    if not s.query(Enrollment).filter_by(course_id=course_id,student_id=student_id).first():raise HTTPException(403)
    row=s.query(Attendance).filter_by(course_id=course_id,student_id=student_id,session_date=session_date).first()
    if not row:row=Attendance(course_id=course_id,student_id=student_id,session_date=session_date);s.add(row)
    row.status=status;row.recorded_by=u.id;audit(s,u,'attendance',str(course_id));s.commit()
    return RedirectResponse(f'/courses/{course_id}',303)

@app.post('/courses/{course_id}/grades')
def record_grade(course_id:int,student_id:int=Form(...),kind:str=Form(...),title:str=Form(...),value:float=Form(...),maximum:float=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    if u.role in ('ta','admin'):raise HTTPException(403,'Only academic staff may record grades')
    if kind not in ('cat','quiz','assignment','exam') or not (0<maximum<=100000) or not (0<=value<=maximum):raise HTTPException(400)
    if not s.query(Enrollment).filter_by(course_id=course_id,student_id=student_id).first():raise HTTPException(403)
    row=s.query(Assessment).filter_by(course_id=course_id,student_id=student_id,kind=kind,title=title).first()
    if not row:row=Assessment(course_id=course_id,student_id=student_id,kind=kind,title=title);s.add(row)
    row.score=value;row.max_score=maximum;audit(s,u,'grade',f'{course_id}:{student_id}:{title}');s.commit()
    return RedirectResponse(f'/courses/{course_id}',303)

@app.post('/courses/{course_id}/topics')
def add_topic(course_id:int,title:str=Form(...),planned_hours:float=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    if u.role in ('ta','admin') or not (0<planned_hours<=1000):raise HTTPException(403)
    s.add(Topic(course_id=course_id,title=title,planned_hours=planned_hours));audit(s,u,'add_topic',title);s.commit();return RedirectResponse(f'/courses/{course_id}',303)
@app.post('/topics/{topic_id}/progress')
def progress(topic_id:int,completed_hours:float=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    t=s.get(Topic,topic_id)
    if not t:raise HTTPException(404)
    require_course(s,u,t.course_id)
    if u.role in ('ta','admin') or not (0<=completed_hours<=t.planned_hours):raise HTTPException(403)
    t.completed_hours=completed_hours;audit(s,u,'topic_progress',str(topic_id));s.commit();return RedirectResponse(f'/courses/{t.course_id}',303)

@app.post('/curricula')
async def upload_curriculum(programme:str=Form(...),version:str=Form(...),file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    if u.role not in ('dean','hod','admin') or (u.role=='hod' and u.programme!=programme):raise HTTPException(403)
    raw=await file.read()
    if len(raw)>5_000_000:raise HTTPException(413)
    if programme not in ('Economics','Finance','Accounting'):raise HTTPException(400,'Unknown programme')
    ext=Path(file.filename).suffix.lower()
    try:
        if ext=='.txt':content=raw.decode('utf-8')
        elif ext=='.docx':
            from docx import Document
            content='\n'.join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        elif ext in ('.xlsx','.csv'):
            rows=parse_tabular_upload(file.filename,raw)
            content='\n'.join(' | '.join(f'{k}: {v}' for k,v in row.items()) for row in rows)
        elif ext=='.pdf':
            from pypdf import PdfReader
            content='\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(raw)).pages)
        else:raise ValueError('Supported: TXT, DOCX, PDF, CSV, XLSX')
    except Exception as e:raise HTTPException(400,str(e))
    s.add(Curriculum(programme=programme,version=version,filename=Path(file.filename).name[:200],content=content[:500000],uploaded_by=u.id));audit(s,u,'curriculum_upload',programme);s.commit();return RedirectResponse('/',303)

@app.get('/api/courses/{course_id}/risk')
def risk_api(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    c=require_course(s,u,course_id)
    return {'course':c.code,'students':[{'student_no':st.student_no,**score(s,c.id,st.id)} for st in roster(s,c.id)]}

@app.get('/api/courses/{course_id}/risk.csv')
def risk_csv(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    c=require_course(s,u,course_id);buf=io.StringIO();w=csv.writer(buf);w.writerow(['student_no','attendance','assessment','risk','classification'])
    for st in roster(s,c.id):
        r=score(s,c.id,st.id);w.writerow([st.student_no,r['attendance'],r['assessment'],r['risk'],r['label']])
    return StreamingResponse(iter([buf.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{c.code}_risk.csv"'})

@app.post('/courses/{course_id}/interventions')
def intervention(course_id:int,student_id:int=Form(...),note:str=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    if u.role in ('ta','admin'):raise HTTPException(403)
    if not s.query(Enrollment).filter_by(course_id=course_id,student_id=student_id).first():raise HTTPException(403)
    s.add(Intervention(student_id=student_id,course_id=course_id,note=note[:2000],created_by=u.id));audit(s,u,'intervention',str(student_id));s.commit()
    return RedirectResponse(f'/courses/{course_id}',303)

def parse_tabular_upload(filename,raw):
    if len(raw)>5_000_000:raise HTTPException(413,'File exceeds 5MB')
    try:
        if filename.lower().endswith('.csv'):
            return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        if filename.lower().endswith('.xlsx'):
            from openpyxl import load_workbook
            wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
            vals=wb.active.values
            headers=[str(v).strip() if v is not None else '' for v in next(vals)]
            return [dict(zip(headers,r)) for r in vals if any(v is not None for v in r)]
    except Exception as exc:raise HTTPException(400,f'Invalid spreadsheet: {exc}')
    raise HTTPException(400,'Only CSV or XLSX supported')

def week_report(s,course_id):
    rows=s.query(WeeklyCoverage).filter_by(course_id=course_id).order_by(WeeklyCoverage.week_no).all()
    planned=sum(x.planned_hours for x in rows)
    done=sum(min(x.delivered_hours,x.planned_hours) for x in rows)
    return {'course_id':course_id,'total_planned_hours':round(planned,2),'total_delivered_hours':round(done,2),
            'coverage_percent':round(100*done/planned,1) if planned else None,
            'target_percent':85,'weeks':[{'week':x.week_no,'topic':x.planned_topic,'planned_hours':x.planned_hours,'delivered_hours':x.delivered_hours,'notes':x.delivery_notes} for x in rows]}

@app.post('/courses/{course_id}/attendance/import')
async def attendance_import(course_id:int,file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    rows=parse_tabular_upload(file.filename or '',await file.read())
    required={'student_no','session_date','status'}
    if not rows or not required.issubset(rows[0]):raise HTTPException(400,'Columns required: student_no,session_date,status')
    if len(rows)>10000:raise HTTPException(400,'Too many rows')
    parsed=[];seen=set();errors=[]
    for i,row in enumerate(rows,2):
        try:
            no=str(row['student_no']).strip(); day=str(row['session_date']).strip(); status=str(row['status']).strip().lower()
            if isinstance(row['session_date'],datetime):day=row['session_date'].date().isoformat()
            date.fromisoformat(day)
            if status not in ('present','absent','late'):raise ValueError('status must be present/absent/late')
            student=s.query(Student).filter_by(student_no=no).first()
            if not student or not s.query(Enrollment).filter_by(course_id=course_id,student_id=student.id).first():raise ValueError('student not enrolled in this offering')
            key=(student.id,day)
            if key in seen:raise ValueError('duplicate student/date in file')
            seen.add(key);parsed.append((student.id,day,status))
        except Exception as exc:errors.append(f'Row {i}: {exc}')
    if errors:raise HTTPException(422,{'message':'Nothing imported; correct the spreadsheet','errors':errors[:30]})
    for student_id,day,status in parsed:
        obj=s.query(Attendance).filter_by(course_id=course_id,student_id=student_id,session_date=day).first()
        if obj is None:obj=Attendance(course_id=course_id,student_id=student_id,session_date=day);s.add(obj)
        obj.status=status;obj.recorded_by=u.id
    audit(s,u,'attendance_bulk_import',f'{course_id}: {len(parsed)} records');s.commit()
    return RedirectResponse(f'/courses/{course_id}',303)

# Two-step preview/confirm workflow. Uploads remain staged until explicit confirmation.
from import_preview import attendance_rows, profile_rows

@app.post('/courses/{course_id}/imports/preview',response_class=HTMLResponse)
async def preview_import(course_id:int,request:Request,kind:str=Form(...),file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    course=require_course(s,u,course_id)
    if kind not in ('attendance','profiles'):raise HTTPException(400,'Unsupported import type')
    rows=parse_tabular_upload(file.filename or '',await file.read())
    if kind=='attendance':
        enrolled={st.student_no:st.id for st in roster(s,course_id)}
        cleaned,errors=attendance_rows(rows,enrolled)
    else:
        existing={}
        for st in s.query(Student).filter_by(programme=course.programme).all():
            profile=s.query(StudentProfile).filter_by(student_id=st.id).first()
            existing[st.student_no]={'name':st.name,'programme':st.programme,**({field:getattr(profile,field) for field in ('email','phone','intake','session')} if profile else {})}
        cleaned,errors=profile_rows(rows,course.programme,existing,validate_roster_rows)
        schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
        if schedule:
            for i,record in enumerate(cleaned,2):
                if record['intake'] and record['intake']!=schedule.intake:errors.append(f'Row {i}: intake does not match offering')
                if record['session'] and record['session']!=schedule.session:errors.append(f'Row {i}: session does not match offering')
    token=None
    if cleaned and not errors:
        token=secrets.token_urlsafe(32)
        s.add(PendingImport(id=token,user_id=u.id,course_id=course_id,import_type=kind,payload=json.dumps(cleaned),filename=Path(file.filename or '').name[:200]))
        s.commit()
    return templates.TemplateResponse(request,'import_preview.html',{'course':course,'kind':kind,'rows':cleaned[:30],'count':len(cleaned),'errors':errors[:40],'token':token,'csrf':request.session.get('csrf','')})

@app.post('/courses/{course_id}/imports/{token}/confirm')
def confirm_import(course_id:int,token:str,u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    course=require_course(s,u,course_id)
    staged=s.get(PendingImport,token)
    if not staged or staged.course_id!=course_id or staged.user_id!=u.id:raise HTTPException(404,'Import preview not found')
    if datetime.utcnow()-staged.created_at>timedelta(minutes=30):
        s.delete(staged);s.commit();raise HTTPException(410,'Preview expired; upload again')
    records=json.loads(staged.payload)
    try:
        if staged.import_type=='attendance':
            enrolled={st.student_no:st.id for st in roster(s,course_id)}
            records,errors=attendance_rows(records,enrolled)
            if errors:raise HTTPException(422,{'errors':errors})
            for record in records:
                sid=enrolled[record['student_no']]
                item=s.query(Attendance).filter_by(student_id=sid,course_id=course_id,session_date=record['session_date']).first()
                if item is None:
                    item=Attendance(student_id=sid,course_id=course_id,session_date=record['session_date']);s.add(item)
                item.status=record['status'];item.recorded_by=u.id
        elif staged.import_type=='profiles':
            existing={}
            for st in s.query(Student).filter_by(programme=course.programme).all():
                profile=s.query(StudentProfile).filter_by(student_id=st.id).first()
                existing[st.student_no]={'name':st.name,'programme':st.programme,**({field:getattr(profile,field) for field in ('email','phone','intake','session')} if profile else {})}
            records,errors=profile_rows(records,course.programme,existing,validate_roster_rows)
            schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
            if schedule:
                for i,r in enumerate(records,2):
                    if r['intake'] and r['intake']!=schedule.intake:errors.append(f'Row {i}: intake mismatch')
                    if r['session'] and r['session']!=schedule.session:errors.append(f'Row {i}: session mismatch')
            if errors:raise HTTPException(422,{'errors':errors})
            for record in records:
                student=s.query(Student).filter_by(student_no=record['student_no']).first()
                if student is None:
                    student=Student(student_no=record['student_no'],name=record['name'],programme=record['programme']);s.add(student);s.flush()
                if not s.query(Enrollment).filter_by(student_id=student.id,course_id=course_id).first():
                    s.add(Enrollment(student_id=student.id,course_id=course_id))
                if any(record[field] for field in ('email','phone','intake','session')):
                    profile=s.query(StudentProfile).filter_by(student_id=student.id).first()
                    if profile is None:profile=StudentProfile(student_id=student.id);s.add(profile)
                    for field in ('email','phone','intake','session'):
                        if record[field]:setattr(profile,field,record[field])
                    profile.updated_by=u.id
        else:raise HTTPException(400,'Unsupported import type')
        audit(s,u,'confirmed_import',f'{staged.import_type} course={course_id} rows={len(records)} file={staged.filename}')
        s.delete(staged);s.commit()
    except Exception:
        s.rollback();raise
    return RedirectResponse(f'/courses/{course_id}',303)

@app.post('/courses/{course_id}/weekly/import')
async def weekly_import(course_id:int,file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    require_course(s,u,course_id)
    if u.role in ('ta','admin'):raise HTTPException(403,'Lecturer/HOD/Dean only')
    rows=parse_tabular_upload(file.filename or '',await file.read())
    required={'week_no','planned_topic','planned_hours','delivered_hours'}
    if not rows or not required.issubset(rows[0]):raise HTTPException(400,'Columns required: week_no,planned_topic,planned_hours,delivered_hours')
    if len(rows)>500:raise HTTPException(400,'Too many rows')
    schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
    parsed=[];seen=set();errors=[]
    for i,row in enumerate(rows,2):
        try:
            week=int(row['week_no']);topic=str(row['planned_topic']).strip();planned=float(row['planned_hours']);delivered=float(row['delivered_hours'] or 0)
            if not topic or len(topic)>300 or not (1<=week<=(schedule.weeks if schedule else 52)) or not (0<planned<=100) or not (0<=delivered<=planned):raise ValueError('invalid week/topic/hours')
            key=(week,topic)
            if key in seen:raise ValueError('duplicate week/topic')
            seen.add(key);parsed.append((week,topic,planned,delivered,str(row.get('delivery_notes') or '')[:2000]))
        except Exception as exc:errors.append(f'Row {i}: {exc}')
    if errors:raise HTTPException(422,{'message':'Nothing imported','errors':errors[:30]})
    for week,topic,planned,delivered,notes in parsed:
        obj=s.query(WeeklyCoverage).filter_by(course_id=course_id,week_no=week,planned_topic=topic).first()
        if obj is None:obj=WeeklyCoverage(course_id=course_id,week_no=week,planned_topic=topic);s.add(obj)
        obj.planned_hours=planned;obj.delivered_hours=delivered;obj.delivery_notes=notes;obj.updated_by=u.id
    audit(s,u,'weekly_coverage_import',f'{course_id}: {len(parsed)} topics');s.commit()
    return RedirectResponse(f'/courses/{course_id}',303)

@app.get('/api/courses/{course_id}/weekly-coverage')
def weekly_coverage(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    require_course(s,u,course_id)
    return week_report(s,course_id)

@app.get('/api/weekly-coverage')
def school_weekly_coverage(session_type:Optional[str]=None,intake:Optional[str]=None,module:Optional[str]=None,u:User=Depends(actor),s:Session=Depends(db)):
    result=[]
    for course in s.query(Course).all():
        if not allowed(u,course):continue
        schedule=s.query(OfferingSchedule).filter_by(course_id=course.id).first()
        if session_type and (not schedule or schedule.session!=session_type):continue
        if intake and (not schedule or schedule.intake!=intake):continue
        if module and (not schedule or schedule.module!=module):continue
        report=week_report(s,course.id)
        result.append({'course':course.code,'programme':course.programme,'session':schedule.session if schedule else None,
                       'intake':schedule.intake if schedule else None,'module':schedule.module if schedule else None,**report})
    return {'courses':result}

@app.get('/health')
def health():return {'status':'ok'}

@app.get('/api/courses/{course_id}/coverage')
def coverage_api(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    c=require_course(s,u,course_id)
    topics=s.query(Topic).filter_by(course_id=course_id).all()
    planned=sum(t.planned_hours for t in topics)
    done=sum(min(t.completed_hours,t.planned_hours) for t in topics)
    return {'course':c.code,'planned_hours':planned,'completed_hours':done,
            'coverage_percent':round(100*done/planned,1) if planned else None,
            'target_percent':85,'topics':[{'title':t.title,'planned':t.planned_hours,'completed':t.completed_hours} for t in topics]}

@app.get('/api/courses/{course_id}/ai-brief')
async def ai_brief(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    """Optional Claude summary. Only aggregates, never student identifiers, are sent."""
    if u.role not in ('dean','hod','lecturer'):raise HTTPException(403)
    c=require_course(s,u,course_id)
    stats=[score(s,c.id,st.id) for st in roster(s,c.id)]
    counts={label:sum(x['label']==label for x in stats) for label in ('low','moderate','high','critical','insufficient data')}
    coverage=coverage_api(course_id,u,s)
    facts={'course':c.code,'students':len(stats),'risk_counts':counts,'coverage_percent':coverage['coverage_percent']}
    api_key=os.getenv('ANTHROPIC_API_KEY')
    if not api_key:return {'mode':'offline','facts':facts,'message':'Configure ANTHROPIC_API_KEY to enable AI summaries.'}
    import httpx
    prompt='Provide a cautious academic support summary, under 180 words, based only on these aggregate facts. Do not invent causes or individual details. Include that lecturer review is required: '+json.dumps(facts)
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response=await client.post('https://api.anthropic.com/v1/messages',headers={'x-api-key':api_key,'anthropic-version':'2023-06-01','content-type':'application/json'},json={'model':os.getenv('ANTHROPIC_MODEL','claude-haiku-4-5-20251001'),'max_tokens':300,'messages':[{'role':'user','content':prompt}]})
            response.raise_for_status()
            data=response.json()
        return {'mode':'claude','facts':facts,'summary':' '.join(b.get('text','') for b in data.get('content',[]) if b.get('type')=='text')}
    except (httpx.HTTPError,KeyError,ValueError):
        return JSONResponse(status_code=502,content={'detail':'AI provider unavailable; underlying academic records are unaffected.'})


@app.get('/api/curriculum-catalogue')
def curriculum_catalogue(programme:str,u:User=Depends(actor)):
    """Approved 2023 curriculum only. No historical versions are exposed."""
    if u.role not in ('dean','hod','admin','lecturer','ta') or (u.role=='hod' and u.programme!=programme):raise HTTPException(403)
    from floated_modules import catalogue
    try: rows=catalogue(ROOT,programme)
    except ValueError as e:raise HTTPException(400,str(e))
    return {'programme':programme,'version':'2023','approval_status':'approved','modules':rows,'count':len(rows),'note':'Verify blank credit fields against signed curriculum before scheduling.'}

@app.post('/api/float-module')
def float_module(programme:str=Form(...),module_code:str=Form(...),academic_year:str=Form(...),intake:str=Form(...),session_type:str=Form(...),module_block:str=Form(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    """Authorized academic office publishes a module for a particular cohort/session."""
    if u.role not in ('dean','hod','admin') or (u.role=='hod' and u.programme!=programme):raise HTTPException(403)
    if session_type not in ('morning','evening','weekend'):raise HTTPException(400,'Invalid session')
    if not all((academic_year.strip(),intake.strip(),module_block.strip())):raise HTTPException(400,'Academic year, intake and block required')
    from floated_modules import find_module
    try: row=find_module(ROOT,programme,module_code)
    except ValueError as e:raise HTTPException(400,str(e))
    if not row:raise HTTPException(400,'Only approved 2023 curriculum modules may be floated')
    existing=s.query(FloatedModule).filter_by(programme=programme,module_code=row['module_code'],academic_year=academic_year.strip(),intake=intake.strip(),session=session_type,module_block=module_block.strip()).first()
    if existing:
        existing.status='floated'
    else:
        s.add(FloatedModule(programme=programme,module_code=row['module_code'],academic_year=academic_year.strip(),intake=intake.strip(),session=session_type,module_block=module_block.strip(),status='floated',created_by=u.id))
    audit(s,u,'float_module',f"{programme}:{row['module_code']}:{intake}:{session_type}:{module_block}")
    s.commit()
    return {'status':'floated','programme':programme,'curriculum_version':'2023','module_code':row['module_code'],'module_title':row['module_title']}

@app.get('/api/floated-modules')
def floated_modules(programme:str,intake:str='',session_type:str='',module_block:str='',academic_year:str='',u:User=Depends(actor),s:Session=Depends(db)):
    if programme not in ('Economics','Finance','Accounting'):raise HTTPException(400)
    if u.role=='hod' and u.programme!=programme:raise HTTPException(403)
    if u.role in ('ta','lecturer') and u.programme!=programme:raise HTTPException(403)
    query=s.query(FloatedModule).filter_by(programme=programme,status='floated')
    if intake:query=query.filter_by(intake=intake)
    if session_type:query=query.filter_by(session=session_type)
    if module_block:query=query.filter_by(module_block=module_block)
    if academic_year:query=query.filter_by(academic_year=academic_year)
    from floated_modules import find_module
    rows=[]
    for f in query.all():
        m=find_module(ROOT,programme,f.module_code)
        if m:rows.append({'float_id':f.id,'module_code':f.module_code,'module_title':m['module_title'],'credits':m['credits'],'intake':f.intake,'session':f.session,'module_block':f.module_block,'academic_year':f.academic_year})
    return {'curriculum_version':'2023','programme':programme,'floated_modules':rows,'count':len(rows)}

@app.get('/curricula/{curriculum_id}',response_class=HTMLResponse)
def curriculum_page(curriculum_id:int,request:Request,u:User=Depends(actor),s:Session=Depends(db)):
    item=s.get(Curriculum,curriculum_id)
    if not item:raise HTTPException(404)
    if u.role not in ('admin','dean') and u.programme!=item.programme:raise HTTPException(403)
    return templates.TemplateResponse(request,'curriculum.html',{'item':item,'user':u,'csrf':request.session.get('csrf','')})

@app.get('/api/dashboard')
def dashboard_api(u:User=Depends(actor),s:Session=Depends(db)):
    if u.role=='admin':raise HTTPException(403,'Technical administrators cannot access academic analytics')
    courses=[c for c in s.query(Course).all() if allowed(u,c)]
    result=[]
    for c in courses:
        students=roster(s,c.id)
        stats=[score(s,c.id,st.id) for st in students]
        topics=s.query(Topic).filter_by(course_id=c.id).all()
        planned=sum(t.planned_hours for t in topics)
        completed=sum(min(t.completed_hours,t.planned_hours) for t in topics)
        result.append({'course_id':c.id,'code':c.code,'programme':c.programme,'enrollments':len(students),'high_or_critical':sum(r['label'] in ('high','critical') for r in stats),'insufficient_data':sum(r['risk'] is None for r in stats),'coverage_percent':round(100*completed/planned,1) if planned else None})
    return {'courses':result,'note':'Risk categories are provisional and not validated predictions. Enrolments may include the same student across courses.'}

# Standalone modular calendar preview; no ERP/LMS dependency.
from modular_calendar import generate_calendar

@app.get('/api/modular-calendar/preview')
def modular_calendar_preview(start_date:str,session_type:str,credits:int,break_minutes:int=0,
                             before_cat:int=10,after_cat:int=5,evening_extra_days:int=1,
                             start_time:str|None=None,end_time:str|None=None,
                             extra_days_before_cat:int|None=None,weekdays:str|None=None,
                             excluded_dates:str|None=None,coverage_target:float=85,
                             u:User=Depends(actor)):
    try:
        return generate_calendar(start_date,session_type,credits,break_minutes=break_minutes,
                                 before_cat=before_cat,after_cat=after_cat,evening_extra_days=evening_extra_days,
                                 start_time=start_time,end_time=end_time,extra_days_before_cat=extra_days_before_cat,
                                 weekdays=[int(x.strip()) for x in weekdays.split(',')] if weekdays else None,
                                 excluded_dates=[x.strip() for x in excluded_dates.split(',')] if excluded_dates else None,
                                 coverage_target=coverage_target)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


# Version 0.12: calendar-aware monitoring; no synthetic attendance is generated.
from academic_monitor import monitor

@app.get('/api/courses/{course_id}/academic-monitor')
def course_academic_monitor(course_id:int, credits:Optional[int]=None, as_of:Optional[str]=None,
                            break_minutes:int=0, before_cat:int=10, after_cat:int=5,
                            evening_extra_days:int=1, weekdays:Optional[str]=None,
                            excluded_dates:Optional[str]=None,
                            u:User=Depends(actor), s:Session=Depends(db)):
    require_course(s,u,course_id)
    offering=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
    if not offering: raise HTTPException(422,'Course has no configured modular schedule')
    configured=s.get(OfferingCreditConfig,course_id)
    if configured:
        if credits is not None and credits != configured.credits: raise HTTPException(409,'Credits conflict with verified offering configuration')
        credits=configured.credits
    if credits not in (10,15): raise HTTPException(422,'Offering requires verified 10 or 15 credit configuration')
    try:
        cal=generate_calendar(offering.start_date,offering.session,credits,
            break_minutes=break_minutes,before_cat=before_cat,after_cat=after_cat,
            evening_extra_days=evening_extra_days,
            weekdays=[int(x.strip()) for x in weekdays.split(',')] if weekdays else None,
            excluded_dates=[x.strip() for x in excluded_dates.split(',')] if excluded_dates else None)
        if as_of:date.fromisoformat(as_of)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    students=[r.student_id for r in s.query(Enrollment).filter_by(course_id=course_id).all()]
    attendance=[{'student_id':r.student_id,'session_date':r.session_date,'status':r.status}
                for r in s.query(Attendance).filter_by(course_id=course_id).all()]
    coverage=[{'planned_hours':r.planned_hours,'delivered_hours':r.delivered_hours}
              for r in s.query(WeeklyCoverage).filter_by(course_id=course_id).all()]
    return {'course_id':course_id,'course_code':s.get(Course,course_id).code,
            'session':offering.session,'intake':offering.intake,'module':offering.module,
            **monitor(cal,students,attendance,coverage,as_of=as_of)}

@app.get('/api/academic-monitor')
def school_academic_monitor(credits:Optional[int]=None,session_type:Optional[str]=None,
                            intake:Optional[str]=None,module:Optional[str]=None,
                            as_of:Optional[str]=None,u:User=Depends(actor),s:Session=Depends(db)):
    # Credit hours must be explicitly supplied until credits are verified and
    # persisted per floated offering. Do not silently assume 10 or 15 credits.
    result=[]
    for c in s.query(Course).all():
        if not allowed(u,c):continue
        schedule=s.query(OfferingSchedule).filter_by(course_id=c.id).first()
        if not schedule:continue
        if session_type and schedule.session!=session_type:continue
        if intake and schedule.intake!=intake:continue
        if module and schedule.module!=module:continue
        if not s.get(OfferingCreditConfig,c.id): continue
        result.append(course_academic_monitor(c.id,None,as_of,u=u,s=s))
    return {'courses':result,'warning':'Unconfigured offerings are excluded; verify their credit values before monitoring.'}


# Version 0.13: role-scoped graphical monitoring overview.
@app.get('/monitor',response_class=HTMLResponse)
def monitoring_dashboard(request:Request, programme:str='',session_type:str='',intake:str='',module:str='',
                         u:User=Depends(actor),s:Session=Depends(db)):
    from dashboard_summary import summarize_offerings
    rows=[]
    for c in s.query(Course).order_by(Course.programme,Course.code).all():
        if not allowed(u,c): continue
        if programme and c.programme!=programme: continue
        schedule=s.query(OfferingSchedule).filter_by(course_id=c.id).first()
        if not schedule: continue
        if session_type and schedule.session!=session_type: continue
        if intake and schedule.intake!=intake: continue
        if module and schedule.module!=module: continue
        enrolments=s.query(Enrollment).filter_by(course_id=c.id).all()
        ids={e.student_id for e in enrolments}
        attendance=s.query(Attendance).filter_by(course_id=c.id).all()
        records=[a for a in attendance if a.student_id in ids]
        topics=s.query(Topic).filter_by(course_id=c.id).all()
        weekly=s.query(WeeklyCoverage).filter_by(course_id=c.id).all()
        if weekly:
            planned=sum(float(w.planned_hours) for w in weekly)
            delivered=sum(min(float(w.delivered_hours),float(w.planned_hours)) for w in weekly)
        else:
            planned=sum(float(x.planned_hours) for x in topics)
            delivered=sum(min(float(x.completed_hours),float(x.planned_hours)) for x in topics)
        coverage=round(100*delivered/planned,1) if planned>0 else None
        present=sum(a.status in ('present','late') for a in records)
        observed=round(100*present/len(records),1) if records else None
        rows.append({'id':c.id,'code':c.code,'title':c.title,'programme':c.programme,
            'session':schedule.session,'intake':schedule.intake,'module':schedule.module,
            'enrolled':len(ids),'coverage':coverage,'attendance':observed,
            'attendance_records':len(records),'planned_hours':round(planned,1),
            'delivered_hours':round(delivered,1),
            'credits':s.get(OfferingCreditConfig,c.id).credits if s.get(OfferingCreditConfig,c.id) else None})
    summary=summarize_offerings(rows)
    return templates.TemplateResponse(request,'monitor.html',{'user':u,'rows':rows,'summary':summary,
        'filters':{'programme':programme,'session_type':session_type,'intake':intake,'module':module},
        'csrf':request.session.get('csrf','')})

@app.get('/monitor.csv')
def monitoring_export(programme:str='',session_type:str='',intake:str='',module:str='',
                      u:User=Depends(actor),s:Session=Depends(db)):
    import csv,io
    output=io.StringIO();writer=csv.writer(output)
    writer.writerow(['Course','Title','Programme','Session','Intake','Module','Enrolled','Coverage percent','Recorded attendance rate percent'])
    for c in s.query(Course).all():
        if not allowed(u,c) or (programme and c.programme!=programme):continue
        sch=s.query(OfferingSchedule).filter_by(course_id=c.id).first()
        if not sch or (session_type and sch.session!=session_type) or (intake and sch.intake!=intake) or (module and sch.module!=module):continue
        ids={e.student_id for e in s.query(Enrollment).filter_by(course_id=c.id).all()}
        att=[a for a in s.query(Attendance).filter_by(course_id=c.id).all() if a.student_id in ids]
        w=s.query(WeeklyCoverage).filter_by(course_id=c.id).all()
        if w:planned=sum(x.planned_hours for x in w);done=sum(min(x.delivered_hours,x.planned_hours) for x in w)
        else:
            ts=s.query(Topic).filter_by(course_id=c.id).all()
            planned=sum(x.planned_hours for x in ts);done=sum(min(x.completed_hours,x.planned_hours) for x in ts)
        writer.writerow([c.code,c.title,c.programme,sch.session,sch.intake,sch.module,len(ids),
                         round(100*done/planned,1) if planned else '',
                         round(100*sum(a.status in ('present','late') for a in att)/len(att),1) if att else ''])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="sefa_monitoring.csv"'})


# Version 0.14: credit verification and weekly trends for each floated offering.
@app.post('/api/courses/{course_id}/credits')
def verify_offering_credits(course_id:int, credits:int=Form(...), u:User=Depends(actor),
                            s:Session=Depends(db), _csrf:None=Depends(check_csrf)):
    course=require_course(s,u,course_id)
    if u.role not in ('dean','admin','hod') or (u.role=='hod' and u.programme!=course.programme):
        raise HTTPException(403,'Only Dean, authorized HOD or administrator may verify credits')
    if credits not in (10,15): raise HTTPException(422,'Only 10 or 15 credits are supported')
    config=s.get(OfferingCreditConfig,course_id)
    if config is None:
        config=OfferingCreditConfig(course_id=course_id,credits=credits,verified_by=u.id)
        s.add(config)
    else:
        config.credits=credits;config.verified_by=u.id;config.verified_at=datetime.utcnow()
    audit(s,u,'verify_offering_credits',f'{course_id}: {credits}')
    s.commit()
    return {'course_id':course_id,'credits':credits,'verified':True}

@app.get('/api/courses/{course_id}/weekly-trends')
def course_weekly_trends(course_id:int, as_of:Optional[str]=None, u:User=Depends(actor),s:Session=Depends(db)):
    require_course(s,u,course_id)
    schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
    config=s.get(OfferingCreditConfig,course_id)
    if not schedule or not config: raise HTTPException(422,'Schedule and verified credits required')
    try:
        cal=generate_calendar(schedule.start_date,schedule.session,config.credits)
        if as_of: date.fromisoformat(as_of)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    from weekly_trends import weekly_trends
    enrollments=[r.student_id for r in s.query(Enrollment).filter_by(course_id=course_id).all()]
    attendance=[{'student_id':r.student_id,'session_date':r.session_date,'status':r.status}
                for r in s.query(Attendance).filter_by(course_id=course_id).all()]
    coverage=[{'week_no':r.week_no,'planned_hours':r.planned_hours,'delivered_hours':r.delivered_hours}
              for r in s.query(WeeklyCoverage).filter_by(course_id=course_id).all()]
    return {'course_id':course_id,'credits':config.credits,'session':schedule.session,
            'weekly':weekly_trends(cal,coverage,attendance,enrollments,as_of=as_of),
            'note':'Weekly teaching-plan numbers are matched to calendar weeks in order; missing coverage and attendance are not zeros.'}


# Version 0.15: verified weekly teaching plans, TA evidence, HOD approval.
@app.post('/courses/{course_id}/teaching-plan/import')
async def teaching_plan_import(course_id:int,file:UploadFile=File(...),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    c=require_course(s,u,course_id)
    if u.role not in ('lecturer','hod','dean'):raise HTTPException(403,'Academic staff only')
    from teaching_workflow import validate_plan_rows
    rows=parse_tabular_upload(file.filename or '',await file.read())
    schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
    try:clean=validate_plan_rows(rows,schedule.weeks if schedule else 52)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    existing=s.query(TeachingPlanItem).filter_by(course_id=course_id).all()
    if any(x.status!='planned' for x in existing):raise HTTPException(409,'Plan already has delivery evidence; revise through an approved change process')
    # Full plan replacement is atomic. Do not silently retain removed topics.
    for x in existing:s.delete(x)
    s.flush()
    for week,topic,hours in clean:
        s.add(TeachingPlanItem(course_id=course_id,week_no=week,planned_topic=topic,planned_hours=hours,updated_by=u.id))
    audit(s,u,'teaching_plan_import',f'course={course_id} topics={len(clean)}')
    s.commit()
    return {'course_id':course_id,'topics_imported':len(clean),'status':'planned'}

@app.post('/api/teaching-plan/{item_id}/report')
def submit_teaching_report(item_id:int,delivered_hours:float=Form(...),notes:str=Form(''),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    item=s.get(TeachingPlanItem,item_id)
    if item is None:raise HTTPException(404,'Topic not found')
    c=require_course(s,u,item.course_id)
    if u.role!='lecturer' or c.lecturer_id!=u.id:raise HTTPException(403,'Assigned lecturer only')
    if item.status=='approved':raise HTTPException(409,'Approved report is locked')
    if not 0<=delivered_hours<=item.planned_hours:raise HTTPException(422,'Delivered hours outside approved plan')
    item.delivered_hours=delivered_hours;item.lecturer_notes=notes[:2000]
    item.status='submitted';item.updated_by=u.id;item.ta_notes='';item.hod_notes='';item.reviewed_by=None
    audit(s,u,'teaching_report_submitted',f'topic={item.id}')
    s.commit();return {'item_id':item.id,'status':item.status}

@app.post('/api/teaching-plan/{item_id}/ta-review')
def verify_teaching_report(item_id:int,decision:str=Form(...),notes:str=Form(''),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    item=s.get(TeachingPlanItem,item_id)
    if item is None:raise HTTPException(404,'Topic not found')
    require_course(s,u,item.course_id)
    if u.role!='ta':raise HTTPException(403,'Assigned TA only')
    if item.status!='submitted':raise HTTPException(409,'Report is not awaiting TA review')
    if decision not in ('verify','return'):raise HTTPException(422,'Decision must be verify or return')
    item.status='ta_verified' if decision=='verify' else 'returned'
    item.ta_notes=notes[:2000];item.reviewed_by=u.id
    audit(s,u,'teaching_report_ta_review',f'topic={item.id} decision={decision}')
    s.commit();return {'item_id':item.id,'status':item.status}

@app.post('/api/teaching-plan/{item_id}/hod-review')
def approve_teaching_report(item_id:int,decision:str=Form(...),notes:str=Form(''),u:User=Depends(actor),s:Session=Depends(db),_csrf:None=Depends(check_csrf)):
    item=s.get(TeachingPlanItem,item_id)
    if item is None:raise HTTPException(404,'Topic not found')
    c=require_course(s,u,item.course_id)
    if u.role not in ('hod','dean'):raise HTTPException(403,'HOD or Dean only')
    if item.status!='ta_verified':raise HTTPException(409,'TA verification required before approval')
    if decision not in ('approve','return'):raise HTTPException(422,'Decision must be approve or return')
    item.status='approved' if decision=='approve' else 'returned'
    item.hod_notes=notes[:2000];item.reviewed_by=u.id
    audit(s,u,'teaching_report_hod_review',f'topic={item.id} decision={decision}')
    s.commit();return {'item_id':item.id,'status':item.status}

@app.get('/api/courses/{course_id}/teaching-plan')
def teaching_plan_status(course_id:int,current_week:int=1,u:User=Depends(actor),s:Session=Depends(db)):
    require_course(s,u,course_id)
    from teaching_workflow import coverage_alerts
    items=s.query(TeachingPlanItem).filter_by(course_id=course_id).order_by(TeachingPlanItem.week_no,TeachingPlanItem.id).all()
    rows=[{'id':x.id,'week_no':x.week_no,'planned_topic':x.planned_topic,'planned_hours':x.planned_hours,'delivered_hours':x.delivered_hours,'status':x.status,'lecturer_notes':x.lecturer_notes,'ta_notes':x.ta_notes,'hod_notes':x.hod_notes} for x in items]
    if not 1<=current_week<=52:raise HTTPException(422,'Invalid current week')
    return {'course_id':course_id,'topics':rows,'monitoring':coverage_alerts(rows,current_week)}


@app.get('/api/dean/verified-coverage')
def dean_verified_coverage(programme:Optional[str]=None,session_type:Optional[str]=None,intake:Optional[str]=None,u:User=Depends(actor),s:Session=Depends(db)):
    """Course-wide HOD/Dean view; only approved teaching hours count."""
    if u.role not in ('dean','hod'):raise HTTPException(403,'Dean or HOD only')
    from teaching_workflow import coverage_alerts
    query=s.query(Course)
    if programme:query=query.filter_by(programme=programme)
    if u.role=='hod' and u.programme:query=query.filter_by(programme=u.programme)
    result=[]
    for c in query.all():
        schedule=s.query(OfferingSchedule).filter_by(course_id=c.id).first()
        if session_type and (not schedule or schedule.session!=session_type):continue
        if intake and (not schedule or schedule.intake!=intake):continue
        items=s.query(TeachingPlanItem).filter_by(course_id=c.id).all()
        rows=[{'week_no':x.week_no,'planned_hours':x.planned_hours,'delivered_hours':x.delivered_hours,'status':x.status} for x in items]
        week=max((x.week_no for x in items),default=1)
        alerts=coverage_alerts(rows,week)
        result.append({'course_id':c.id,'course_code':c.code,'course_title':c.title,'programme':c.programme,
          'session':schedule.session if schedule else None,'intake':schedule.intake if schedule else None,
          'planned_topics':len(items),'approved_topics':sum(x.status=='approved' for x in items),
          'awaiting_ta':sum(x.status=='submitted' for x in items),
          'awaiting_hod':sum(x.status=='ta_verified' for x in items),
          'verified_percent':alerts['verified_percent'],'alerts':alerts['alerts']})
    return {'courses':result,'count':len(result),'coverage_basis':'HOD-approved delivered hours divided by all planned teaching hours'}


# v0.17: explainable, human-reviewed student-support intelligence.
from risk_intelligence import analyze_student, aggregate_reports

def student_intelligence(s, course_id, student_id):
    attendance=[{'status':x.status,'date':x.session_date} for x in s.query(Attendance).filter_by(course_id=course_id,student_id=student_id).all()]
    assessments=[{'score':x.score,'max_score':x.max_score,'kind':x.kind} for x in s.query(Assessment).filter_by(course_id=course_id,student_id=student_id).all()]
    interventions=[{'status':x.status} for x in s.query(Intervention).filter_by(course_id=course_id,student_id=student_id).all()]
    schedule=s.query(OfferingSchedule).filter_by(course_id=course_id).first()
    config=s.get(OfferingCreditConfig,course_id)
    scheduled_dates=None
    if schedule and config:
        from modular_calendar import generate_calendar
        try:
            calendar=generate_calendar(schedule.start_date,schedule.session,config.credits)
            scheduled_dates=[x['date'] for x in calendar['days'] if x['activity']=='teaching']
        except ValueError:
            pass  # Unverified timetable: do not silently treat unscheduled days as absent.
    return analyze_student(attendance,assessments,interventions,scheduled_dates=scheduled_dates)

@app.get('/api/courses/{course_id}/ai-risk')
def ai_risk_course(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    course=require_course(s,u,course_id)
    if u.role=='admin':raise HTTPException(403,'Technical administrators cannot access student analytics')
    rows=[{'student_no':st.student_no,'name':st.name,**student_intelligence(s,course_id,st.id)} for st in roster(s,course_id)]
    return {'course_id':course_id,'course':course.code,'summary':aggregate_reports(rows),'students':rows,'disclaimer':'Academic-support indicators require human review; never use as sole basis for sanctions, exclusion, grading or admission.'}

@app.get('/api/courses/{course_id}/ai-risk.csv')
def ai_risk_export(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    data=ai_risk_course(course_id,u,s)
    out=io.StringIO();w=csv.writer(out)
    w.writerow(['student_no','risk_index','risk_band','attendance_percent','assessment_percent','recorded_sessions','valid_assessments','open_interventions','explanations','suggested_support'])
    for x in data['students']:
        w.writerow([x['student_no'],x['risk_index'],x['risk_band'],x['attendance_percent'],x['assessment_percent'],x['recorded_sessions'],x['valid_assessments'],x['open_interventions'],'; '.join(x['reasons']),'; '.join(x['suggested_support'])])
    audit(s,u,'ai_risk_export',str(course_id));s.commit()
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="course_{course_id}_support_triage.csv"','Cache-Control':'no-store'})

@app.get('/api/dean/ai-risk-summary')
def dean_ai_risk_summary(programme:Optional[str]=None,u:User=Depends(actor),s:Session=Depends(db)):
    if u.role not in ('dean','hod'):raise HTTPException(403)
    courses=[c for c in s.query(Course).all() if allowed(u,c) and (not programme or c.programme==programme)]
    output=[]
    for c in courses:
        rows=[student_intelligence(s,c.id,st.id) for st in roster(s,c.id)]
        output.append({'course_id':c.id,'code':c.code,'programme':c.programme,**aggregate_reports(rows)})
    return {'courses':output,'note':'Counts are per-course enrolments, not unique students. No individual student identifiers in this summary.'}

@app.get('/ai-risk',response_class=HTMLResponse)
def ai_risk_page(request:Request,u:User=Depends(actor),s:Session=Depends(db)):
    if u.role=='admin':raise HTTPException(403)
    courses=[{'id':c.id,'code':c.code,'programme':c.programme} for c in s.query(Course).all() if allowed(u,c)]
    return templates.TemplateResponse(request,'ai_risk.html',{'user':u,'courses':courses})


# v0.18: risk-data quality and historical validation, with explicit outcome labels.
from risk_validation import quality_report, validate_outcomes
from pydantic import BaseModel, Field

class HistoricalOutcome(BaseModel):
    course_id: int
    student_no: str = Field(min_length=1,max_length=60)
    adverse_outcome: bool

class ValidationBatch(BaseModel):
    records: list[HistoricalOutcome] = Field(min_length=1,max_length=10000)
    threshold: str = 'high'

@app.get('/api/courses/{course_id}/ai-risk-quality')
def ai_risk_quality(course_id:int,u:User=Depends(actor),s:Session=Depends(db)):
    report=ai_risk_course(course_id,u,s)
    return {'course_id':course_id,'quality':quality_report(report['students']),
            'warning':'Completeness reflects available records, not the total number of scheduled classes.'}

@app.post('/api/dean/ai-risk-validation')
def ai_risk_validation(payload:ValidationBatch,request:Request,u:User=Depends(actor),s:Session=Depends(db)):
    if not request.session.get('csrf') or not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),request.session['csrf']):
        raise HTTPException(403,'CSRF token required')
    if u.role not in ('dean','hod'):raise HTTPException(403)
    raise HTTPException(409,'Historical validation disabled until timestamped pre-outcome feature snapshots and outcome dates are available. Current data may leak future information.')
