from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, 'sqlite')(lambda type_, compiler, **kw: 'JSON')

from app.core.config import settings
from app.core.enums import UserRole
from app.db.database import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.base import Base
from app.models.user import User

engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

with SessionLocal() as db:
    user = User(user_code='USR-TEST01', name='Admin Tester', email='ppsdev6@gmail.com', mobile='+919876543210', role=UserRole.ADMIN, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

req = client.post('/api/v1/admin/auth/otp/request', json={'identifier': 'ppsdev6@gmail.com'})
print('REQUEST', req.status_code, req.json())
otp = req.json()['data']['dev_otp']
login = client.post('/api/v1/admin/auth/otp/verify', json={'identifier': 'ppsdev6@gmail.com', 'otp': otp})
print('LOGIN', login.status_code, login.json())
print('SET_COOKIE', login.headers.get('set-cookie'))
print('COOKIE_NAME', settings.REFRESH_COOKIE_NAME)
print('COOKIE_VALUE', login.cookies.get(settings.REFRESH_COOKIE_NAME))

with SessionLocal() as db:
    sessions = db.query(AuthSession).all()
    print('DB_SESSIONS', [(str(s.id), s.user_id, s.actor_type, s.refresh_token_hash[:20], s.revoked_at, s.expires_at) for s in sessions])

refresh = client.post('/api/v1/sessions/refresh', cookies=login.cookies)
print('REFRESH', refresh.status_code)
print(refresh.text)

app.dependency_overrides.clear()
