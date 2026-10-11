"""One local school model. Real child/contact data should not be entered into demo accounts."""
import hashlib
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[1] / '.local' / 'guardian.sqlite3'
DEMO_PASSWORD = 'AirDemo2026!'


@contextmanager
def connection():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS schools(id TEXT PRIMARY KEY,name TEXT,lat REAL,lon REAL);
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, role TEXT, school TEXT, class_id TEXT, salt TEXT, password TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL);
    CREATE TABLE IF NOT EXISTS children(id TEXT PRIMARY KEY, parent_id TEXT REFERENCES users(id), school TEXT, class_id TEXT, alias TEXT, age_group TEXT, caution INTEGER DEFAULT 0, budget REAL DEFAULT 1500);
    CREATE TABLE IF NOT EXISTS classes(id TEXT PRIMARY KEY, school TEXT, label TEXT);
    CREATE TABLE IF NOT EXISTS preferences(user_id TEXT PRIMARY KEY REFERENCES users(id), body TEXT);
    CREATE TABLE IF NOT EXISTS school_state(school TEXT PRIMARY KEY, mode TEXT DEFAULT 'demo', polluted INTEGER DEFAULT 0, override TEXT, override_reason TEXT, updated REAL);
    CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, school TEXT, flag TEXT, kind TEXT, day TEXT, created REAL, body TEXT);
    CREATE TABLE IF NOT EXISTS alert_state(school TEXT PRIMARY KEY, flag TEXT, morning_day TEXT);
    CREATE TABLE IF NOT EXISTS deliveries(event_id TEXT, user_id TEXT, channel TEXT, status TEXT, body TEXT, PRIMARY KEY(event_id,user_id,channel));
    CREATE TABLE IF NOT EXISTS push_subscriptions(user_id TEXT PRIMARY KEY REFERENCES users(id), endpoint TEXT, p256dh TEXT, auth TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS plan_reviews(event_id TEXT,user_id TEXT,created REAL,PRIMARY KEY(event_id,user_id));
    CREATE TABLE IF NOT EXISTS plan_share_tokens(token_hash TEXT PRIMARY KEY,event_id TEXT,user_id TEXT REFERENCES users(id),expires REAL,used REAL);
    CREATE TABLE IF NOT EXISTS acknowledgments(event_id TEXT, class_id TEXT, user_id TEXT, created REAL, PRIMARY KEY(event_id,class_id));
    CREATE TABLE IF NOT EXISTS history(id TEXT PRIMARY KEY, school TEXT, user_id TEXT, action TEXT, created REAL, body TEXT);
    CREATE TABLE IF NOT EXISTS exposure(id TEXT PRIMARY KEY, child_id TEXT REFERENCES children(id), day TEXT, context TEXT, minutes INTEGER, concentration REAL, created REAL);
    CREATE TABLE IF NOT EXISTS checkins(id TEXT PRIMARY KEY, child_id TEXT REFERENCES children(id), day TEXT, signal INTEGER, created REAL);
    CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, school TEXT, user_id TEXT, category TEXT, note TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS sensor_readings(id TEXT PRIMARY KEY, school TEXT, class_id TEXT, pm25 REAL, observed REAL, source TEXT);
    CREATE TABLE IF NOT EXISTS login_attempts(user_id TEXT PRIMARY KEY, count INTEGER, updated REAL);
    CREATE TABLE IF NOT EXISTS schedule_changes(class_id TEXT,day TEXT,minutes INTEGER,event_id TEXT,PRIMARY KEY(class_id,day));
    ''')
    if "override_until" not in [r[1] for r in db.execute("PRAGMA table_info(school_state)")]:
        db.execute("ALTER TABLE school_state ADD COLUMN override_until REAL")
    from backend.functions.air_engine import SCHOOLS
    for school in SCHOOLS.values():
        db.execute('INSERT OR IGNORE INTO schools VALUES (?,?,?,?)',(school['id'],school['name'],school['lat'],school['lon']))
    db.execute('DELETE FROM checkins WHERE created<?',(time.time()-30*86400,))
    if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        for name, role, school, class_id in [('parent','parent','riverdale',None),('teacher','teacher','riverdale','class-a'),
                                            ('staff','staff','riverdale',None),('admin','admin','riverdale',None),
                                            ('parent-other','parent','greenwood',None)]:
            salt=secrets.token_hex(16)
            digest=hashlib.pbkdf2_hmac('sha256',DEMO_PASSWORD.encode(),bytes.fromhex(salt),200000).hex()
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?)',(name,role,school,class_id,salt,digest))
        for row in [('class-a','riverdale','Class 3 A'),('class-b','riverdale','Class 6 B'),('class-m','greenwood','Class 4 A')]:
            db.execute('INSERT INTO classes VALUES (?,?,?)',row)
        for row in [('child-a','parent','riverdale','class-a','Child A','5-8',0,1500),('child-b','parent','riverdale','class-b','Child B','9-12',1,1500),('child-m','parent-other','greenwood','class-m','Child M','9-12',0,1500)]:
            db.execute('INSERT INTO children VALUES (?,?,?,?,?,?,?,?)',row)
        for school in ('riverdale','greenwood','horizon'):
            db.execute('INSERT INTO school_state(school,updated) VALUES (?,?)',(school,time.time()))
        db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def configured_school(school_id):
    with connection() as db:
        row=db.execute('SELECT * FROM schools WHERE id=?',(school_id,)).fetchone()
    return dict(row) if row else None
