import os
import json
import time
import hmac
import hashlib
import smtplib
import secrets
import sqlite3
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from functools import wraps
from collections import defaultdict
from flask import (Flask, redirect, url_for, session, request,
                   render_template, abort, g, jsonify, send_from_directory)
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from dotenv import load_dotenv

from curriculum_content import DAYS, REVIEW_BY_DAY
import game_content
import learning_content

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
# Session cookie hardening: HTTPS-only, no JS access, and SameSite=Lax so
# cross-site POSTs can't ride the admin's session (CSRF) while the top-level
# OAuth redirect back from Google still carries the cookie.
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# ── Google OAuth ──────────────────────────────────────────────────────────────
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ['GOOGLE_CLIENT_ID'],
    client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE = os.path.join(os.path.dirname(__file__), 'members.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
        # A live game means a whole room writing answers within the same second.
        # WAL lets readers and writers work at once, and a busy timeout makes the
        # rare lock wait its turn instead of erroring out under the load.
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA busy_timeout=5000')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id   TEXT UNIQUE NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            grade       TEXT,
            division    TEXT,
            role        TEXT DEFAULT 'student',
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- Pending school-email verifications. One row per Google account that
        -- has signed in but not yet proven a Stratford email. Server-side (never
        -- the client cookie) so the 6-digit code cannot be read or brute-forced.
        CREATE TABLE IF NOT EXISTS email_verifications (
            google_id   TEXT PRIMARY KEY,
            email       TEXT NOT NULL,
            name        TEXT NOT NULL,
            grade       TEXT NOT NULL,
            role        TEXT NOT NULL,
            code_hash   TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            attempts    INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            author_id   INTEGER NOT NULL,
            pinned      INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL,
            description TEXT,
            category    TEXT DEFAULT 'General',
            author_id   INTEGER NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS meetings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            topic       TEXT NOT NULL,
            location    TEXT,
            status      TEXT DEFAULT 'scheduled',
            notes       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- ── Curriculum (the 20 day course) ───────────────────────────────
        CREATE TABLE IF NOT EXISTS curriculum_days (
            day            INTEGER PRIMARY KEY,
            title          TEXT NOT NULL,
            hook           TEXT,
            topics         TEXT,            -- JSON array of strings
            activity_title TEXT,
            activity_desc  TEXT,
            tool_name      TEXT,
            tool_url       TEXT,
            game           TEXT,            -- quiz | poll | wager | jeopardy | NULL
            game_set       TEXT
        );
        -- ── Learn mode progress (the only per-account progress) ──────────
        CREATE TABLE IF NOT EXISTS learning_progress (
            user_id      INTEGER NOT NULL,
            day          INTEGER NOT NULL,
            correct      INTEGER DEFAULT 0,   -- best auto-graded score
            total        INTEGER DEFAULT 0,   -- number of auto-graded questions
            completed    INTEGER DEFAULT 0,
            attempts     INTEGER DEFAULT 0,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, day)
        );
        -- ── Live game sessions ───────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS live_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            host_id     INTEGER NOT NULL,
            game_type   TEXT NOT NULL,
            set_id      TEXT,
            title       TEXT,
            day         INTEGER,
            status      TEXT DEFAULT 'lobby',   -- lobby | active | ended
            phase       TEXT DEFAULT 'lobby',   -- lobby | question | reveal | podium
            q_index     INTEGER DEFAULT 0,
            locked      INTEGER DEFAULT 0,
            q_started_at REAL,
            ver         INTEGER DEFAULT 0,
            content     TEXT,                   -- JSON snapshot of the game set
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS live_players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            user_id     INTEGER,
            name        TEXT NOT NULL,
            team        TEXT DEFAULT '',
            joined_at   REAL,
            last_seen   REAL
        );
        CREATE TABLE IF NOT EXISTS live_answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            player_id   INTEGER NOT NULL,
            q_index     INTEGER NOT NULL,
            answer      TEXT,
            value       REAL,
            correct     INTEGER,
            points      INTEGER DEFAULT 0,
            wager       INTEGER,
            response_ms INTEGER,
            created_at  REAL,
            UNIQUE(session_id, player_id, q_index)
        );
    ''')
    db.commit()

    # Add the review_set column to any curriculum_days table created before this
    # feature existed (fresh installs get it from a later re-seed either way).
    if 'review_set' not in {r[1] for r in db.execute('PRAGMA table_info(curriculum_days)').fetchall()}:
        db.execute('ALTER TABLE curriculum_days ADD COLUMN review_set TEXT')
        db.commit()

    # Track the last real activity on a live game so idle ones auto-close.
    if 'last_active' not in {r[1] for r in db.execute('PRAGMA table_info(live_sessions)').fetchall()}:
        db.execute('ALTER TABLE live_sessions ADD COLUMN last_active REAL')
        db.commit()

    # Seed or refresh the curriculum from curriculum_content.py. This never
    # overwrites an admin's per-day tool_url override (see the day link editor).
    for d in DAYS:
        db.execute('''
            INSERT INTO curriculum_days
                (day, title, hook, topics, activity_title, activity_desc, tool_name, tool_url, game, game_set, review_set)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(day) DO UPDATE SET
                title=excluded.title, hook=excluded.hook, topics=excluded.topics,
                activity_title=excluded.activity_title, activity_desc=excluded.activity_desc,
                tool_name=excluded.tool_name, game=excluded.game, game_set=excluded.game_set,
                review_set=excluded.review_set
        ''', (d['day'], d['title'], d['hook'], json.dumps(d['topics']),
              d['activity']['title'], d['activity']['desc'],
              d['activity']['tool'], d['activity']['url'], d['game'], d['game_set'],
              REVIEW_BY_DAY.get(d['day'])))
    db.commit()

    # Migrate away from the removed Colab and Kaggle activities. A row that still
    # points at one of those (or the old R2D3 link) is pulled back to the current
    # default, which now points at an in-house lab. Genuine admin overrides do not
    # contain these domains, so they are left untouched.
    _dead = ('colab.research.google.com', 'kaggle.com', 'r2d3.us')
    for d in DAYS:
        row = db.execute('SELECT tool_url FROM curriculum_days WHERE day=?', (d['day'],)).fetchone()
        if row and row[0] and any(s in row[0] for s in _dead):
            db.execute('UPDATE curriculum_days SET tool_url=?, tool_name=? WHERE day=?',
                       (d['activity']['url'], d['activity']['tool'], d['day']))
    db.commit()

    db.close()

# ── Auth helpers ──────────────────────────────────────────────────────────────
def get_current_user():
    if 'user_id' not in session:
        return None
    return get_db().execute('SELECT * FROM users WHERE id = ?',
                            (session['user_id'],)).fetchone()

# ── School-email verification ──────────────────────────────────────────────────
# Google login proves identity on any account; a one-time code to a Stratford
# email proves the person is actually a student. That is our workaround for the
# school G Suite not approving domain OAuth: consumer Google sign-in still works,
# and the emailed code is the membership gate.
SCHOOL_DOMAINS = ('@stratfordschools.net', '@stratfordschools.com')
CODE_TTL_MIN   = 15          # a verification code is valid for 15 minutes
MAX_CODE_TRIES = 6           # wrong-code attempts before the code is burned

def is_school_email(email):
    return email.lower().endswith(SCHOOL_DOMAINS)

def _now():
    return datetime.now(timezone.utc)

def hash_code(code):
    # Keyed hash so a stolen DB row can't be brute-forced without SECRET_KEY.
    return hmac.new(app.secret_key.encode(), code.encode(),
                    hashlib.sha256).hexdigest()

def send_email(to_addr, subject, body):
    """Send mail via SMTP if configured in .env, else log the body (dev mode).

    Configure by adding to .env: SMTP_HOST, SMTP_PORT (default 587), SMTP_USER,
    SMTP_PASS, and optionally SMTP_FROM. Until those exist, the code is written
    to the service log so the flow is testable but real delivery is off.
    """
    host = os.environ.get('SMTP_HOST')
    user = os.environ.get('SMTP_USER')
    pw   = os.environ.get('SMTP_PASS')
    sender = os.environ.get('SMTP_FROM', user or 'no-reply@spbdatascience.org')
    if not (host and user and pw):
        app.logger.warning('SMTP not configured; would email %s: %s | %s',
                            to_addr, subject, body)
        return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = sender
    msg['To']      = to_addr
    msg.set_content(body)
    port = int(os.environ.get('SMTP_PORT', '587'))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as s:
                s.login(user, pw)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls()
                s.login(user, pw)
                s.send_message(msg)
        return True
    except Exception as e:
        app.logger.error('send_email to %s failed: %s', to_addr, e)
        return False

def issue_code(db, google_id, email, name, grade, role_req, google_email):
    """Generate a fresh 6-digit code, store its hash server-side, email it."""
    admin_emails = [e.strip() for e in
                    os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()]
    role = 'admin' if google_email in admin_emails else role_req
    # secrets, not random: this code is the membership gate, so it needs a
    # CSPRNG. random is a Mersenne Twister and its stream is reconstructable
    # from observed output; an attacker can request codes at their own address.
    code = f'{secrets.randbelow(1000000):06d}'
    expires = (_now() + timedelta(minutes=CODE_TTL_MIN)).isoformat()
    db.execute('''
        INSERT INTO email_verifications
            (google_id, email, name, grade, role, code_hash, expires_at, attempts)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(google_id) DO UPDATE SET
            email=excluded.email, name=excluded.name, grade=excluded.grade,
            role=excluded.role, code_hash=excluded.code_hash,
            expires_at=excluded.expires_at, attempts=0,
            created_at=CURRENT_TIMESTAMP
    ''', (google_id, email, name, grade, role, hash_code(code), expires))
    db.commit()
    send_email(email, 'Your SPB Data Science Club verification code',
               'Your verification code is {}\n\n'
               'Enter it on the club site to finish joining. It expires in {} '
               'minutes.\n\nIf you did not request this, you can ignore this '
               'email.'.format(code, CODE_TTL_MIN))


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        if user['status'] == 'pending':
            return redirect(url_for('pending'))
        if user['status'] == 'rejected':
            return redirect(url_for('rejected'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user['role'] != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


# Curriculum now sits behind a sign-in like the rest of the member area: you
# log in with any Google account, then the sign-up form gates membership on a
# school email. So the curriculum wall is just login_required under another name.
curriculum_required = login_required


@app.context_processor
def inject_globals():
    user = get_current_user()
    pending_count = 0
    if user and user['role'] == 'admin':
        pending_count = get_db().execute(
            "SELECT COUNT(*) FROM users WHERE status='pending'"
        ).fetchone()[0]
    return dict(current_user=user, pending_count=pending_count)

# ── Public routes ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    user = get_current_user()
    if user and user['status'] == 'approved':
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    user = get_current_user()
    if user:
        if user['status'] == 'approved':
            return redirect(url_for('announcements'))
        if user['status'] == 'pending':
            return redirect(url_for('pending'))
    note = ('That sign-in did not go through. Please try again.'
            if request.args.get('auth_error') else None)
    return render_template('login.html', note=note)

@app.route('/auth/google')
def auth_google():
    redirect_uri = url_for('auth_callback', _external=True,
                           _scheme='https')
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    # A stale login tab, a double-submitted callback, or a bot hitting this URL
    # directly makes authorize_access_token() raise (e.g. mismatching CSRF state).
    # Treat that as a failed sign-in and send them back to login, not a 500.
    try:
        token = google.authorize_access_token()
    except OAuthError:
        return redirect(url_for('login', auth_error='1'))
    info = token['userinfo']
    db = get_db()
    # Remember the Google email on every sign-in so the school-domain curriculum
    # gate works for members and guests alike.
    session['google_email'] = info.get('email', '')
    session['google_name']  = info.get('name', '')
    user = db.execute('SELECT * FROM users WHERE google_id = ?',
                      (info['sub'],)).fetchone()
    if user:
        session['user_id'] = user['id']
        if user['status'] == 'approved':
            return redirect(url_for('announcements'))
        if user['status'] == 'pending':
            return redirect(url_for('pending'))
        return redirect(url_for('rejected'))

    session['google_id']    = info['sub']
    return redirect(url_for('complete_profile'))

@app.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    if 'google_id' not in session:
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        grade        = request.form.get('grade', '').strip()
        school_email = request.form.get('school_email', '').strip().lower()
        role_req     = request.form.get('role', 'student').strip()
        if role_req not in ('student', 'teacher'):
            role_req = 'student'

        # Any Google account can be here; the school email is what we verify.
        if not all([name, grade, school_email]):
            error = 'Name, grade, and school email are all required.'
        elif not is_school_email(school_email):
            error = ('Please use your school email ending in '
                     '@stratfordschools.net or @stratfordschools.com.')
        else:
            db = get_db()
            taken = db.execute('SELECT 1 FROM users WHERE email = ?',
                               (school_email,)).fetchone()
            if taken:
                error = 'That school email is already linked to an account.'
            else:
                # Email a code and hold the details server-side until it is
                # confirmed. The account is only created on the verify step.
                issue_code(db, session['google_id'], school_email, name, grade,
                           role_req, session.get('google_email', ''))
                return redirect(url_for('verify_email'))

    return render_template('complete_profile.html',
                           google_name=session.get('google_name', ''),
                           google_email=session.get('google_email', ''),
                           error=error)

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'google_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    row = db.execute('SELECT * FROM email_verifications WHERE google_id = ?',
                     (session['google_id'],)).fetchone()
    if not row:
        # Nothing pending (already verified, or they skipped the form).
        return redirect(url_for('complete_profile'))

    error = None
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if _now() > datetime.fromisoformat(row['expires_at']):
            error = 'That code has expired. Send yourself a new one.'
        elif row['attempts'] >= MAX_CODE_TRIES:
            error = 'Too many incorrect attempts. Send a new code.'
        elif not hmac.compare_digest(hash_code(code), row['code_hash']):
            db.execute('UPDATE email_verifications SET attempts = attempts + 1 '
                       'WHERE google_id = ?', (row['google_id'],))
            db.commit()
            error = 'That code is not right. Try again.'
        else:
            # Verified: create the approved account, keyed to this Google id.
            try:
                db.execute('''
                    INSERT INTO users
                        (google_id, email, name, grade, division, role, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'approved')
                ''', (row['google_id'], row['email'], row['name'],
                      row['grade'], '', row['role']))
                db.execute('DELETE FROM email_verifications WHERE google_id = ?',
                           (row['google_id'],))
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                return redirect(url_for('login', auth_error='dupe'))
            user = db.execute('SELECT * FROM users WHERE google_id = ?',
                              (row['google_id'],)).fetchone()
            session['user_id'] = user['id']
            for k in ('google_id', 'google_email', 'google_name'):
                session.pop(k, None)
            return redirect(url_for('announcements'))

    if error is None and request.args.get('too_soon'):
        error = ('A code was just sent. Wait a minute before asking for '
                 'another one, and check your spam folder.')
    return render_template('verify_email.html', email=row['email'], error=error)

# Minimum gap between two code emails for the same Google account. Without this,
# every click of Resend sent real mail to a student address AND reset attempts to
# 0, so it was both a mail-bomb primitive and a way to reset the wrong-code
# counter indefinitely. created_at is refreshed by issue_code on every send.
RESEND_COOLDOWN_SEC = 60

@app.route('/verify-email/resend', methods=['POST'])
def resend_code():
    if 'google_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    row = db.execute('SELECT * FROM email_verifications WHERE google_id = ?',
                     (session['google_id'],)).fetchone()
    if row:
        # created_at is written by SQLite's CURRENT_TIMESTAMP, which is UTC but
        # naive; compare it against a naive UTC now.
        try:
            last = datetime.fromisoformat(row['created_at'])
        except (TypeError, ValueError):
            last = None
        age = ((_now().replace(tzinfo=None) - last).total_seconds()
               if last else RESEND_COOLDOWN_SEC)
        if age < RESEND_COOLDOWN_SEC:
            return redirect(url_for('verify_email', too_soon='1'))
        issue_code(db, row['google_id'], row['email'], row['name'],
                   row['grade'], row['role'], session.get('google_email', ''))
    return redirect(url_for('verify_email'))

@app.route('/pending')
def pending():
    return render_template('pending.html')

@app.route('/rejected')
def rejected():
    return render_template('rejected.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/announcements')
@login_required
def announcements():
    db = get_db()
    items = db.execute('''
        SELECT a.*, u.name AS author_name
        FROM announcements a JOIN users u ON a.author_id = u.id
        ORDER BY a.pinned DESC, a.created_at DESC
    ''').fetchall()
    return render_template('announcements.html', items=items, active='announcements')

@app.route('/resources')
@login_required
def resources():
    db = get_db()
    rows = db.execute('''
        SELECT r.*, u.name AS author_name
        FROM resources r JOIN users u ON r.author_id = u.id
        ORDER BY r.category, r.created_at DESC
    ''').fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['category']].append(row)
    return render_template('resources.html', grouped=dict(grouped), active='resources')

@app.route('/schedule')
@login_required
def schedule():
    db = get_db()
    items = db.execute('SELECT * FROM meetings ORDER BY date ASC').fetchall()
    return render_template('schedule.html', items=items, active='schedule')

@app.route('/members')
@login_required
def members():
    db = get_db()
    all_members = db.execute(
        "SELECT * FROM users WHERE status='approved' ORDER BY name ASC"
    ).fetchall()
    admins   = [m for m in all_members if m['role'] == 'admin']
    teachers = [m for m in all_members if m['role'] == 'teacher']
    students = [m for m in all_members if m['role'] == 'student']
    return render_template('members.html', admins=admins, teachers=teachers,
                           students=students, active='members')

# ── Admin ─────────────────────────────────────────────────────────────────────
@app.route('/admin/pending')
@login_required
@admin_required
def admin_pending():
    db = get_db()
    pending = db.execute(
        "SELECT * FROM users WHERE status='pending' ORDER BY created_at ASC"
    ).fetchall()
    return render_template('admin/pending.html', pending=pending,
                           active='admin_pending')

@app.route('/admin/approve/<int:uid>', methods=['POST'])
@login_required
@admin_required
def admin_approve(uid):
    role = request.form.get('role', 'student')
    if role not in ('student', 'teacher', 'admin'):
        role = 'student'
    db = get_db()
    db.execute("UPDATE users SET status='approved', role=? WHERE id=?", (role, uid))
    db.commit()
    return redirect(url_for('admin_pending'))

@app.route('/admin/reject/<int:uid>', methods=['POST'])
@login_required
@admin_required
def admin_reject(uid):
    get_db().execute("UPDATE users SET status='rejected' WHERE id=?", (uid,))
    get_db().commit()
    return redirect(url_for('admin_pending'))

@app.route('/admin/user/role/<int:uid>', methods=['POST'])
@login_required
@admin_required
def admin_change_role(uid):
    role = request.form.get('role', 'student')
    if role in ('student', 'teacher', 'admin'):
        db = get_db()
        db.execute('UPDATE users SET role=? WHERE id=?', (role, uid))
        db.commit()
    return redirect(url_for('members'))

@app.route('/admin/announcement/post', methods=['POST'])
@login_required
@admin_required
def admin_post_announcement():
    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    pinned  = 1 if request.form.get('pinned') else 0
    user    = get_current_user()
    if title and content:
        get_db().execute(
            'INSERT INTO announcements (title, content, author_id, pinned) VALUES (?,?,?,?)',
            (title, content, user['id'], pinned))
        get_db().commit()
    return redirect(url_for('announcements'))

@app.route('/admin/announcement/delete/<int:aid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_announcement(aid):
    get_db().execute('DELETE FROM announcements WHERE id=?', (aid,))
    get_db().commit()
    return redirect(url_for('announcements'))

@app.route('/admin/announcement/pin/<int:aid>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_pin(aid):
    db  = get_db()
    ann = db.execute('SELECT pinned FROM announcements WHERE id=?', (aid,)).fetchone()
    if ann:
        db.execute('UPDATE announcements SET pinned=? WHERE id=?',
                   (0 if ann['pinned'] else 1, aid))
        db.commit()
    return redirect(url_for('announcements'))

@app.route('/admin/resource/add', methods=['POST'])
@login_required
@admin_required
def admin_add_resource():
    title    = request.form.get('title', '').strip()
    url_val  = request.form.get('url', '').strip()
    desc     = request.form.get('description', '').strip()
    category = request.form.get('category', 'General').strip()
    user     = get_current_user()
    if title and url_val:
        get_db().execute(
            'INSERT INTO resources (title, url, description, category, author_id) VALUES (?,?,?,?,?)',
            (title, url_val, desc, category, user['id']))
        get_db().commit()
    return redirect(url_for('resources'))

@app.route('/admin/resource/delete/<int:rid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_resource(rid):
    get_db().execute('DELETE FROM resources WHERE id=?', (rid,))
    get_db().commit()
    return redirect(url_for('resources'))

@app.route('/admin/meeting/add', methods=['POST'])
@login_required
@admin_required
def admin_add_meeting():
    date     = request.form.get('date', '').strip()
    topic    = request.form.get('topic', '').strip()
    location = request.form.get('location', '').strip()
    notes    = request.form.get('notes', '').strip()
    if date and topic:
        get_db().execute(
            'INSERT INTO meetings (date, topic, location, notes) VALUES (?,?,?,?)',
            (date, topic, location, notes))
        get_db().commit()
    return redirect(url_for('schedule'))

@app.route('/admin/meeting/cancel/<int:mid>', methods=['POST'])
@login_required
@admin_required
def admin_cancel_meeting(mid):
    db  = get_db()
    row = db.execute('SELECT status FROM meetings WHERE id=?', (mid,)).fetchone()
    if row:
        new = 'canceled' if row['status'] == 'scheduled' else 'scheduled'
        db.execute('UPDATE meetings SET status=? WHERE id=?', (new, mid))
        db.commit()
    return redirect(url_for('schedule'))

@app.route('/admin/meeting/delete/<int:mid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_meeting(mid):
    get_db().execute('DELETE FROM meetings WHERE id=?', (mid,))
    get_db().commit()
    return redirect(url_for('schedule'))

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    db   = get_db()
    user = get_current_user()
    next_meeting = db.execute(
        "SELECT * FROM meetings WHERE date >= date('now') ORDER BY date ASC LIMIT 1"
    ).fetchone()
    latest = db.execute('''
        SELECT a.*, u.name AS author_name
        FROM announcements a JOIN users u ON a.author_id = u.id
        ORDER BY a.pinned DESC, a.created_at DESC LIMIT 3
    ''').fetchall()
    recent_resources = db.execute(
        'SELECT * FROM resources ORDER BY created_at DESC LIMIT 4'
    ).fetchall()
    total_days = db.execute('SELECT COUNT(*) FROM curriculum_days').fetchone()[0]
    live = active_session(db)
    learn = _learn_summary(db, user['id'])
    return render_template('dashboard.html', active='dashboard',
                           next_meeting=next_meeting, latest=latest,
                           recent_resources=recent_resources,
                           total_days=total_days, live=live, learn=learn)


# ── Curriculum ────────────────────────────────────────────────────────────────
def _day_row(db, day):
    row = db.execute('SELECT * FROM curriculum_days WHERE day=?', (day,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d['topics'] = json.loads(d['topics'] or '[]')
    except (ValueError, TypeError):
        d['topics'] = []
    return d


@app.route('/curriculum')
@curriculum_required
def curriculum():
    db = get_db()
    rows = db.execute('SELECT * FROM curriculum_days ORDER BY day ASC').fetchall()
    days = []
    for r in rows:
        d = dict(r)
        try:
            d['topics'] = json.loads(d['topics'] or '[]')
        except (ValueError, TypeError):
            d['topics'] = []
        days.append(d)
    return render_template('curriculum.html', active='curriculum', days=days)


@app.route('/curriculum/day/<int:day>')
@curriculum_required
def curriculum_day(day):
    db = get_db()
    d = _day_row(db, day)
    if not d:
        abort(404)
    total = db.execute('SELECT COUNT(*) FROM curriculum_days').fetchone()[0]
    return render_template('curriculum_day.html', active='curriculum', d=d, total=total)


@app.route('/admin/day/<int:day>/link', methods=['POST'])
@login_required
@admin_required
def admin_day_link(day):
    # Lets a host point the day's activity at a fresh Colab or Google Form
    # without touching the source file. Hook text can be tweaked here too.
    db = get_db()
    db.execute('UPDATE curriculum_days SET tool_url=?, tool_name=? WHERE day=?',
               (request.form.get('tool_url', '').strip(),
                request.form.get('tool_name', '').strip() or 'Activity', day))
    db.commit()
    return redirect(url_for('curriculum_day', day=day))


# ── Live game engine ──────────────────────────────────────────────────────────
# A Kahoot style session that everyone joins from their own device. The host
# drives it from a console and every client short polls for the current state,
# which keeps the whole thing running on the existing sync server with no extra
# infrastructure.

def gen_code():
    # Ambiguous characters left out so a code is easy to read off a projector.
    alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(5))


# A live game with no host action, join, or answer for this long closes itself.
IDLE_SECONDS = 600  # 10 minutes


def _expire_if_idle(db, sess):
    """End a game that has been inactive past IDLE_SECONDS. Returns the possibly
    refreshed row (now status 'ended') so callers report the closed game.
    A NULL last_active (legacy rows created before the column existed) is treated
    as expired so a stale session can never linger as a phantom open console."""
    if not sess or sess['status'] == 'ended':
        return sess
    last = sess['last_active']
    if last is None or (time.time() - last) > IDLE_SECONDS:
        db.execute("UPDATE live_sessions SET status='ended', phase='podium' WHERE id=?",
                   (sess['id'],))
        db.commit()
        return db.execute('SELECT * FROM live_sessions WHERE id=?', (sess['id'],)).fetchone()
    return sess


def active_session(db):
    sess = db.execute(
        "SELECT * FROM live_sessions WHERE status IN ('lobby','active') "
        "ORDER BY id DESC LIMIT 1").fetchone()
    sess = _expire_if_idle(db, sess)
    return sess if sess and sess['status'] in ('lobby', 'active') else None


def _session(db, code):
    return db.execute('SELECT * FROM live_sessions WHERE code=?', (code,)).fetchone()


def _bump(db, code):
    # Any host action or join counts as activity and refreshes the idle clock.
    db.execute('UPDATE live_sessions SET ver = ver + 1, last_active = ? WHERE code=?',
               (time.time(), code))


def _content(sess):
    try:
        return json.loads(sess['content'] or '{}')
    except (ValueError, TypeError):
        return {}


def _player_score(db, sid, pid, start_score=0):
    row = db.execute('SELECT COALESCE(SUM(points),0) AS s FROM live_answers '
                     'WHERE session_id=? AND player_id=?', (sid, pid)).fetchone()
    return start_score + (row['s'] or 0)


def _my_player(db, sess):
    key = 'lp_' + sess['code']
    pid = session.get(key)
    if not pid:
        return None
    return db.execute('SELECT * FROM live_players WHERE id=? AND session_id=?',
                      (pid, sess['id'])).fetchone()


def _leaderboard(db, sess, limit=None):
    start = _content(sess).get('start_score', 0)
    rows = db.execute('SELECT * FROM live_players WHERE session_id=? ORDER BY joined_at', (sess['id'],)).fetchall()
    board = [{'name': r['name'], 'team': r['team'],
              'score': _player_score(db, sess['id'], r['id'], start)} for r in rows]
    board.sort(key=lambda x: x['score'], reverse=True)
    if limit:
        board = board[:limit]
    return board


# ---- Host side ----------------------------------------------------------------
@app.route('/games')
@login_required
def games():
    db = get_db()
    user = get_current_user()
    live = active_session(db)
    ctx = dict(active='games', live=live)
    if user['role'] == 'admin':
        ctx['quiz_sets'] = game_content.sets_for('quiz')
        ctx['poll_sets'] = game_content.sets_for('poll')
        ctx['wager_sets'] = game_content.sets_for('wager')
        ctx['jeopardy_sets'] = game_content.JEOPARDY_SETS
    return render_template('games.html', **ctx)


@app.route('/live/new', methods=['POST'])
@login_required
@admin_required
def live_new():
    db = get_db()
    user = get_current_user()
    gtype = request.form.get('game_type', '')
    set_id = request.form.get('set_id', '')
    day = request.form.get('day', type=int)
    cset = game_content.get_set(set_id)
    if not cset or cset['type'] != gtype:
        abort(400)
    # Retire any session this host still has open, so there is one game at a time.
    db.execute("UPDATE live_sessions SET status='ended', phase='podium' "
               "WHERE host_id=? AND status IN ('lobby','active')", (user['id'],))
    code = gen_code()
    while _session(db, code):
        code = gen_code()
    db.execute('''INSERT INTO live_sessions (code, host_id, game_type, set_id, title, day, content, last_active)
                  VALUES (?,?,?,?,?,?,?,?)''',
               (code, user['id'], gtype, set_id, cset.get('title', 'Live Game'),
                day, json.dumps(cset), time.time()))
    db.commit()
    return redirect(url_for('live_host', code=code))


def _host_only(db, code):
    sess = _session(db, code)
    user = get_current_user()
    if not sess:
        abort(404)
    if not user or (user['id'] != sess['host_id'] and user['role'] != 'admin'):
        abort(403)
    return sess


@app.route('/host/<code>')
@login_required
@admin_required
def live_host(code):
    db = get_db()
    sess = _host_only(db, code)
    return render_template('live_host.html', active='games', sess=sess,
                           content=_content(sess))


@app.route('/host/<code>/action', methods=['POST'])
@login_required
@admin_required
def live_action(code):
    db = get_db()
    sess = _host_only(db, code)
    action = request.form.get('action') or (request.get_json(silent=True) or {}).get('action')
    content = _content(sess)
    items = content.get('items', [])
    n = len(items)
    qi = sess['q_index']

    if action == 'start':
        db.execute("UPDATE live_sessions SET status='active', phase='question', q_index=0, "
                   "locked=0, q_started_at=? WHERE code=?", (time.time(), code))
    elif action == 'lock':
        db.execute("UPDATE live_sessions SET locked=1 WHERE code=?", (code,))
    elif action == 'reveal':
        if sess['game_type'] == 'poll':
            _score_poll(db, sess, qi)
        db.execute("UPDATE live_sessions SET phase='reveal', locked=1 WHERE code=?", (code,))
    elif action == 'next':
        if qi + 1 >= n:
            db.execute("UPDATE live_sessions SET phase='podium', status='active' WHERE code=?", (code,))
        else:
            db.execute("UPDATE live_sessions SET q_index=?, phase='question', locked=0, "
                       "q_started_at=? WHERE code=?", (qi + 1, time.time(), code))
    elif action == 'end':
        db.execute("UPDATE live_sessions SET status='ended', phase='podium' WHERE code=?", (code,))
    else:
        abort(400)
    _bump(db, code)
    db.commit()
    return jsonify(ok=True)


def _score_poll(db, sess, qi):
    # Award closeness points once, when the host reveals a number question.
    items = _content(sess).get('items', [])
    if qi >= len(items):
        return
    truth = float(items[qi].get('answer', 0))
    rows = db.execute('SELECT * FROM live_answers WHERE session_id=? AND q_index=?',
                      (sess['id'], qi)).fetchall()
    if not rows:
        return
    errs = [(r, abs((r['value'] if r['value'] is not None else 0) - truth)) for r in rows]
    worst = max((e for _, e in errs), default=0) or 1
    for r, e in errs:
        pts = round(1000 * (1 - e / worst)) if worst else 1000
        db.execute('UPDATE live_answers SET correct=?, points=? WHERE id=?',
                   (1 if e == 0 else 0, pts, r['id']))


@app.route('/api/host/<code>')
@login_required
@admin_required
def api_host(code):
    db = get_db()
    sess = _host_only(db, code)
    sess = _expire_if_idle(db, sess)
    content = _content(sess)
    items = content.get('items', [])
    qi = sess['q_index']
    players = db.execute('SELECT * FROM live_players WHERE session_id=? ORDER BY joined_at',
                         (sess['id'],)).fetchall()
    answered = db.execute('SELECT COUNT(*) AS c FROM live_answers WHERE session_id=? AND q_index=?',
                          (sess['id'], qi)).fetchone()['c']
    out = {
        'ver': sess['ver'], 'status': sess['status'], 'phase': sess['phase'],
        'q_index': qi, 'total': len(items), 'locked': bool(sess['locked']),
        'title': sess['title'], 'game_type': sess['game_type'],
        'player_count': len(players), 'answered': answered,
        'players': [p['name'] for p in players],
    }
    if items and qi < len(items):
        it = items[qi]
        out['question'] = {'q': it.get('q'), 'options': it.get('options', []),
                           'note': it.get('note', ''), 'unit': it.get('unit', '')}
        # Live tally of answers per option (hidden correctness until reveal in the UI).
        if sess['game_type'] in ('quiz', 'wager') and it.get('options'):
            tally = [0] * len(it['options'])
            for r in db.execute('SELECT answer FROM live_answers WHERE session_id=? AND q_index=?',
                                (sess['id'], qi)).fetchall():
                try:
                    tally[int(r['answer'])] += 1
                except (ValueError, TypeError, IndexError):
                    pass
            out['tally'] = tally
            out['correct'] = it.get('correct')
        if sess['game_type'] == 'poll':
            vals = [r['value'] for r in db.execute(
                'SELECT value FROM live_answers WHERE session_id=? AND q_index=?',
                (sess['id'], qi)).fetchall() if r['value'] is not None]
            out['poll'] = _poll_stats(vals, it.get('answer'))
    if sess['phase'] in ('reveal', 'podium'):
        out['leaderboard'] = _leaderboard(db, sess)
    return jsonify(out)


def _poll_stats(vals, truth):
    if not vals:
        return {'count': 0, 'avg': None, 'median': None, 'lo': None, 'hi': None, 'truth': truth}
    s = sorted(vals)
    n = len(s)
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return {'count': n, 'avg': round(sum(vals) / n, 1), 'median': median,
            'lo': min(vals), 'hi': max(vals), 'truth': truth}


# ---- Player side --------------------------------------------------------------
@app.route('/live', methods=['GET'])
def live_entry():
    # Public quick join by code, the way a projector code works in Kahoot.
    code = (request.args.get('code') or '').strip().upper()
    if code:
        return redirect(url_for('live_play', code=code))
    db = get_db()
    live = active_session(db)
    return render_template('live_join.html', live=live)


@app.route('/live/<code>')
def live_play(code):
    code = code.upper()
    db = get_db()
    sess = _session(db, code)
    if not sess:
        return render_template('live_join.html', live=active_session(db),
                               error='No game with that code. Check the projector.')
    user = get_current_user()
    me = _my_player(db, sess)
    return render_template('live_play.html', sess=sess, me=me,
                           logged_in=bool(user),
                           user_name=(user['name'] if user else ''))


@app.route('/live/<code>/join', methods=['POST'])
def live_join(code):
    code = code.upper()
    db = get_db()
    sess = _session(db, code)
    if not sess:
        abort(404)
    if sess['status'] == 'ended':
        return jsonify(ok=False, error='This game has ended.'), 400
    user = get_current_user()
    existing = _my_player(db, sess)
    if existing:
        return jsonify(ok=True)
    # Members are already known, guests bring a nickname.
    name = (request.form.get('name') or (user['name'] if user else '')).strip()[:24]
    team = (request.form.get('team') or '').strip()[:24]
    if not name:
        return jsonify(ok=False, error='Enter a name to join.'), 400
    if user:
        prior = db.execute('SELECT * FROM live_players WHERE session_id=? AND user_id=?',
                           (sess['id'], user['id'])).fetchone()
        if prior:
            session['lp_' + code] = prior['id']
            return jsonify(ok=True)
    now = time.time()
    cur = db.execute('INSERT INTO live_players (session_id, user_id, name, team, joined_at, last_seen) '
                     'VALUES (?,?,?,?,?,?)',
                     (sess['id'], user['id'] if user else None, name, team, now, now))
    session['lp_' + code] = cur.lastrowid
    _bump(db, code)
    db.commit()
    return jsonify(ok=True)


@app.route('/api/live/<code>')
def api_live(code):
    code = code.upper()
    db = get_db()
    sess = _session(db, code)
    if not sess:
        return jsonify(ok=False, error='gone'), 404
    sess = _expire_if_idle(db, sess)
    me = _my_player(db, sess)
    content = _content(sess)
    items = content.get('items', [])
    qi = sess['q_index']
    out = {
        'ok': True, 'ver': sess['ver'], 'status': sess['status'], 'phase': sess['phase'],
        'q_index': qi, 'total': len(items), 'locked': bool(sess['locked']),
        'game_type': sess['game_type'], 'title': sess['title'],
        'joined': bool(me), 'name': me['name'] if me else '',
    }
    if me:
        db.execute('UPDATE live_players SET last_seen=? WHERE id=?', (time.time(), me['id']))
        db.commit()
        out['score'] = _player_score(db, sess['id'], me['id'], content.get('start_score', 0))
    if sess['phase'] == 'question' and items and qi < len(items):
        it = items[qi]
        out['question'] = {'q': it.get('q'), 'options': it.get('options', []),
                           'note': it.get('note', ''), 'unit': it.get('unit', ''),
                           'is_number': sess['game_type'] == 'poll',
                           'is_wager': sess['game_type'] == 'wager'}
        if me:
            ans = db.execute('SELECT * FROM live_answers WHERE session_id=? AND player_id=? AND q_index=?',
                             (sess['id'], me['id'], qi)).fetchone()
            out['answered'] = ans is not None
            out['my_answer'] = ans['answer'] if ans else None
    if sess['phase'] in ('reveal', 'podium') and items and qi < len(items):
        it = items[qi]
        out['reveal'] = {'correct': it.get('correct'), 'options': it.get('options', []),
                         'answer': it.get('answer'), 'unit': it.get('unit', '')}
        if me:
            ans = db.execute('SELECT * FROM live_answers WHERE session_id=? AND player_id=? AND q_index=?',
                             (sess['id'], me['id'], qi)).fetchone()
            if ans:
                out['result'] = {'correct': bool(ans['correct']), 'points': ans['points'],
                                 'answer': ans['answer'], 'value': ans['value']}
        if sess['game_type'] == 'poll':
            vals = [r['value'] for r in db.execute(
                'SELECT value FROM live_answers WHERE session_id=? AND q_index=?',
                (sess['id'], qi)).fetchall() if r['value'] is not None]
            out['reveal']['poll'] = _poll_stats(vals, it.get('answer'))
        out['leaderboard'] = _leaderboard(db, sess, limit=10)
    return jsonify(out)


@app.route('/api/live/<code>/answer', methods=['POST'])
def api_answer(code):
    code = code.upper()
    db = get_db()
    sess = _session(db, code)
    if not sess:
        return jsonify(ok=False, error='gone'), 404
    me = _my_player(db, sess)
    if not me:
        return jsonify(ok=False, error='not joined'), 403
    if sess['phase'] != 'question' or sess['locked']:
        return jsonify(ok=False, error='closed'), 409
    content = _content(sess)
    items = content.get('items', [])
    qi = sess['q_index']
    if qi >= len(items):
        return jsonify(ok=False, error='no question'), 400
    # One answer per question.
    if db.execute('SELECT 1 FROM live_answers WHERE session_id=? AND player_id=? AND q_index=?',
                  (sess['id'], me['id'], qi)).fetchone():
        return jsonify(ok=False, error='already'), 409

    body = request.get_json(silent=True) or request.form
    it = items[qi]
    gtype = sess['game_type']
    elapsed_ms = int((time.time() - (sess['q_started_at'] or time.time())) * 1000)
    correct, points, value, wager = None, 0, None, None
    answer = str(body.get('answer', ''))

    if gtype == 'poll':
        try:
            value = float(str(body.get('answer', '')).replace(',', '').strip())
        except (ValueError, TypeError):
            return jsonify(ok=False, error='Enter a number.'), 400
        answer = str(value)
    elif gtype == 'quiz':
        try:
            ai = int(answer)
        except (ValueError, TypeError):
            return jsonify(ok=False, error='bad answer'), 400
        correct = 1 if ai == it.get('correct') else 0
        if correct:
            limit = max(1, int(it.get('seconds', 20)))
            frac = max(0.0, min(1.0, 1 - (elapsed_ms / 1000.0) / limit))
            points = round(500 + 500 * frac)
    elif gtype == 'wager':
        try:
            ai = int(answer)
        except (ValueError, TypeError):
            return jsonify(ok=False, error='bad answer'), 400
        cur_score = _player_score(db, sess['id'], me['id'], content.get('start_score', 0))
        try:
            wager = int(body.get('wager', 0))
        except (ValueError, TypeError):
            wager = 0
        cap = cur_score if cur_score > 100 else 100
        wager = max(100, min(wager, cap))
        correct = 1 if ai == it.get('correct') else 0
        points = wager if correct else -wager

    db.execute('''INSERT OR IGNORE INTO live_answers
                  (session_id, player_id, q_index, answer, value, correct, points, wager, response_ms, created_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?)''',
               (sess['id'], me['id'], qi, answer, value, correct, points, wager, elapsed_ms, time.time()))
    db.execute('UPDATE live_sessions SET last_active=? WHERE id=?', (time.time(), sess['id']))
    db.commit()
    return jsonify(ok=True)


# ── Jeopardy projector game ────────────────────────────────────────────────────
@app.route('/games/jeopardy')
@login_required
@admin_required
def games_jeopardy():
    # The standalone board game, host run on the projector with teams in the room.
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'games'),
                               'jeopardy.html')


# ── Interactive labs ──────────────────────────────────────────────────────────
# Self-contained, in-browser teaching tools that replace the old Colab and
# Kaggle activities. Students open them on their own devices, no accounts, no
# setup, and the host just projects the same page.
import re as _re

@app.route('/labs/<name>')
@curriculum_required
def labs(name):
    if not _re.fullmatch(r'[a-z0-9_-]{1,32}', name):
        abort(404)
    path = os.path.join(os.path.dirname(__file__), 'games', 'labs')
    if not os.path.exists(os.path.join(path, name + '.html')):
        abort(404)
    return send_from_directory(path, name + '.html')


# ── Learn mode (self-study with saved progress) ────────────────────────────────
# The main reason to have an account. Members and admins work through each day's
# lesson and questions, and their score is the only progress saved per account.

def build_lesson(day):
    lesson = learning_content.LESSONS.get(day)
    if not lesson:
        return None
    questions = []
    mcq = game_content.get_set(learning_content.MCQ_SET.get(day, f'day{day}'))
    if mcq:
        for it in mcq['items']:
            questions.append({'type': 'mcq', 'q': it['q'], 'options': it['options'],
                              'correct': it['correct']})
    for a in lesson['apply']:
        questions.append(dict(a))
    return {'teach': lesson['teach'], 'questions': questions}


def public_questions(questions):
    # Strip the answers before sending to the browser so a lesson is a real test.
    out = []
    for q in questions:
        p = {'type': q['type'], 'q': q['q']}
        if q['type'] in ('mcq', 'multi'):
            p['options'] = q['options']
        if q['type'] == 'number':
            p['unit'] = q.get('unit', '')
        out.append(p)
    return out


def _learn_summary(db, user_id):
    row = db.execute(
        'SELECT COUNT(*) AS started, '
        'SUM(completed) AS done, '
        'COALESCE(SUM(correct),0) AS correct, COALESCE(SUM(total),0) AS total '
        'FROM learning_progress WHERE user_id=?', (user_id,)).fetchone()
    total_days = len(learning_content.LESSONS)
    done = row['done'] or 0
    pct = round((row['correct'] / row['total']) * 100) if row['total'] else 0
    return {'done': done, 'total_days': total_days, 'score_pct': pct}


@app.route('/learn')
@login_required
def learn_index():
    db = get_db()
    user = get_current_user()
    prog = {r['day']: r for r in db.execute(
        'SELECT * FROM learning_progress WHERE user_id=?', (user['id'],)).fetchall()}
    days = []
    for d in db.execute('SELECT day, title FROM curriculum_days ORDER BY day').fetchall():
        p = prog.get(d['day'])
        days.append({'day': d['day'], 'title': d['title'],
                     'completed': bool(p and p['completed']),
                     'correct': p['correct'] if p else None,
                     'total': p['total'] if p else None})
    return render_template('learn_index.html', active='learn', days=days,
                           summary=_learn_summary(db, user['id']))


@app.route('/learn/<int:day>')
@login_required
def learn_lesson(day):
    db = get_db()
    user = get_current_user()
    lesson = build_lesson(day)
    d = _day_row(db, day)
    if not lesson or not d:
        abort(404)
    prog = db.execute('SELECT * FROM learning_progress WHERE user_id=? AND day=?',
                      (user['id'], day)).fetchone()
    total = db.execute('SELECT COUNT(*) FROM curriculum_days').fetchone()[0]
    return render_template('learn_lesson.html', active='learn', d=d,
                           teach=lesson['teach'],
                           questions=public_questions(lesson['questions']),
                           prog=prog, total=total)


@app.route('/learn/<int:day>/submit', methods=['POST'])
@login_required
def learn_submit(day):
    db = get_db()
    user = get_current_user()
    lesson = build_lesson(day)
    if not lesson:
        abort(404)
    answers = (request.get_json(silent=True) or {}).get('answers', [])
    results, correct, auto = [], 0, 0
    for i, q in enumerate(lesson['questions']):
        ans = answers[i] if i < len(answers) else None
        r = {'type': q['type'], 'explain': q.get('explain', '')}
        if q['type'] == 'mcq':
            auto += 1
            ok = (ans == q['correct'])
            r['ok'] = ok; r['correct'] = q['correct']
            correct += 1 if ok else 0
        elif q['type'] == 'multi':
            auto += 1
            ok = sorted(ans) == sorted(q['correct']) if isinstance(ans, list) else False
            r['ok'] = ok; r['correct'] = q['correct']
            correct += 1 if ok else 0
        elif q['type'] == 'number':
            auto += 1
            try:
                ok = abs(float(ans) - q['answer']) <= q.get('tol', 0)
            except (TypeError, ValueError):
                ok = False
            r['ok'] = ok; r['correct'] = q['answer']
            correct += 1 if ok else 0
        else:  # short answer, revealed and self-checked
            r['sample'] = q.get('sample', '')
        results.append(r)

    # Keep the best score, mark complete, count the attempt.
    prev = db.execute('SELECT correct, attempts FROM learning_progress WHERE user_id=? AND day=?',
                      (user['id'], day)).fetchone()
    best = max(correct, prev['correct']) if prev else correct
    attempts = (prev['attempts'] + 1) if prev else 1
    db.execute('''INSERT INTO learning_progress (user_id, day, correct, total, completed, attempts, updated_at)
                  VALUES (?,?,?,?,1,?,CURRENT_TIMESTAMP)
                  ON CONFLICT(user_id, day) DO UPDATE SET
                    correct=?, total=?, completed=1, attempts=?, updated_at=CURRENT_TIMESTAMP''',
               (user['id'], day, best, auto, attempts, best, auto, attempts))
    db.commit()
    return jsonify(results=results, correct=correct, auto=auto, best=best)


@app.route('/admin/progress')
@login_required
@admin_required
def admin_progress():
    db = get_db()
    total_days = len(learning_content.LESSONS)
    rows = db.execute('''
        SELECT u.id, u.name, u.role, u.division,
               COALESCE(SUM(lp.completed),0) AS done,
               COALESCE(SUM(lp.correct),0) AS correct,
               COALESCE(SUM(lp.total),0) AS total,
               MAX(lp.updated_at) AS last_active
        FROM users u
        LEFT JOIN learning_progress lp ON lp.user_id = u.id
        WHERE u.status = 'approved'
        GROUP BY u.id
        ORDER BY done DESC, u.name
    ''').fetchall()
    members = []
    for r in rows:
        members.append({'name': r['name'], 'role': r['role'], 'division': r['division'],
                        'done': r['done'], 'total_days': total_days,
                        'score_pct': round((r['correct'] / r['total']) * 100) if r['total'] else None,
                        'last_active': (r['last_active'] or '')[:10]})
    return render_template('admin_progress.html', active='admin_progress',
                           members=members, total_days=total_days)


# ── Demo page ─────────────────────────────────────────────────────────────────
@app.route('/demo')
def demo():
    # Public kiosk for club fairs and advisor meetings - no login needed
    return render_template('demo.html')

# ── Init ──────────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()


@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=15005, debug=False)
