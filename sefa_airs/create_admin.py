import getpass
from app import SessionLocal,User,crypt
s=SessionLocal()
name=input('Admin username: ').strip()
if s.query(User).filter_by(username=name).first():raise SystemExit('Username already exists')
pw=getpass.getpass('Password (12+ characters): ')
if len(pw)<12:raise SystemExit('Password too short')
s.add(User(username=name,password_hash=crypt.hash(pw),role='admin'));s.commit();s.close()
print('Administrator created')
