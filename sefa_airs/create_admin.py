import getpass
from app import SessionLocal,User,crypt
s=SessionLocal()
while True:
    name=input('Admin username: ').strip()
    if not name:print('Username is required');continue
    if s.query(User).filter_by(username=name).first():print('Username already exists');continue
    break
while True:
    pw=getpass.getpass('Password (12+ characters): ')
    if len(pw)<12:print('Password too short; use at least 12 characters');continue
    if getpass.getpass('Repeat password: ')!=pw:print('Passwords do not match');continue
    break
s.add(User(username=name,password_hash=crypt.hash(pw),role='admin'));s.commit();s.close()
print('Administrator created')
