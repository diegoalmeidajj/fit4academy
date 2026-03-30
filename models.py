"""Fit4Academy Models — All database tables and CRUD functions."""

import os
import bcrypt
from datetime import datetime, date
from database import get_connection, is_postgres


def get_db():
    return get_connection()


# ─── Password Hashing ───────────────────────────────────────────

def _hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ─── Database Init ───────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            name        TEXT DEFAULT '',
            email       TEXT DEFAULT '',
            phone       TEXT DEFAULT '',
            role        TEXT DEFAULT 'user',
            permissions TEXT DEFAULT '',
            academy_id  INTEGER DEFAULT 1,
            active      BOOLEAN DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS academies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            owner_id    INTEGER REFERENCES users(id),
            logo        TEXT DEFAULT '',
            address     TEXT DEFAULT '',
            city        TEXT DEFAULT '',
            state       TEXT DEFAULT '',
            zip_code    TEXT DEFAULT '',
            country     TEXT DEFAULT 'United States',
            phone       TEXT DEFAULT '',
            email       TEXT DEFAULT '',
            website     TEXT DEFAULT '',
            timezone    TEXT DEFAULT 'America/Denver',
            currency    TEXT DEFAULT 'USD',
            language    TEXT DEFAULT 'en',
            theme       TEXT DEFAULT 'dark',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS members (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            first_name      TEXT NOT NULL,
            last_name       TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            phone           TEXT DEFAULT '',
            date_of_birth   DATE,
            gender          TEXT DEFAULT '',
            belt_rank_id    INTEGER DEFAULT 1,
            stripes         INTEGER DEFAULT 0,
            membership_status TEXT DEFAULT 'active',
            join_date       DATE DEFAULT CURRENT_DATE,
            emergency_contact TEXT DEFAULT '',
            emergency_phone TEXT DEFAULT '',
            medical_notes   TEXT DEFAULT '',
            photo           TEXT DEFAULT '',
            pin             TEXT DEFAULT '',
            qr_code         TEXT DEFAULT '',
            source          TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            active          BOOLEAN DEFAULT 1,
            webauthn_credential_id TEXT DEFAULT '',
            webauthn_public_key TEXT DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS membership_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            name            TEXT NOT NULL,
            plan_type       TEXT DEFAULT 'monthly',
            price           REAL DEFAULT 0,
            billing_cycle   TEXT DEFAULT 'monthly',
            trial_days      INTEGER DEFAULT 0,
            description     TEXT DEFAULT '',
            active          BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS memberships (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            plan_id         INTEGER REFERENCES membership_plans(id),
            status          TEXT DEFAULT 'active',
            start_date      DATE DEFAULT CURRENT_DATE,
            end_date        DATE,
            auto_renew      BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS classes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            name            TEXT NOT NULL,
            class_type      TEXT DEFAULT 'gi',
            instructor      TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            duration        INTEGER DEFAULT 60,
            max_capacity    INTEGER DEFAULT 30,
            belt_level      TEXT DEFAULT 'all',
            active          BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS class_schedule (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id        INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            day_of_week     INTEGER NOT NULL,
            start_time      TEXT NOT NULL,
            end_time        TEXT NOT NULL,
            active          BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS check_ins (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            class_id        INTEGER REFERENCES classes(id),
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            check_in_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            method          TEXT DEFAULT 'manual',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS belt_ranks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            color           TEXT NOT NULL,
            sort_order      INTEGER DEFAULT 0,
            max_stripes     INTEGER DEFAULT 4,
            min_months      INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS promotions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            from_belt_id    INTEGER REFERENCES belt_ranks(id),
            to_belt_id      INTEGER REFERENCES belt_ranks(id),
            from_stripes    INTEGER DEFAULT 0,
            to_stripes      INTEGER DEFAULT 0,
            promotion_date  DATE DEFAULT CURRENT_DATE,
            promoted_by     TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            membership_id   INTEGER REFERENCES memberships(id),
            amount          REAL NOT NULL,
            method          TEXT DEFAULT 'cash',
            status          TEXT DEFAULT 'completed',
            reference       TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            payment_date    DATE DEFAULT CURRENT_DATE,
            due_date        DATE,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payment_methods (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            method_type     TEXT DEFAULT 'credit_card',
            last4           TEXT DEFAULT '',
            brand           TEXT DEFAULT '',
            stripe_pm_id    TEXT DEFAULT '',
            is_default      BOOLEAN DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prospects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            first_name      TEXT NOT NULL,
            last_name       TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            phone           TEXT DEFAULT '',
            source          TEXT DEFAULT '',
            status          TEXT DEFAULT 'new',
            interested_in   TEXT DEFAULT '',
            member_id       INTEGER,
            follow_up_date  DATE,
            notes           TEXT DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            name            TEXT NOT NULL,
            event_type      TEXT DEFAULT 'seminar',
            description     TEXT DEFAULT '',
            event_date      DATE,
            start_time      TEXT DEFAULT '',
            end_time        TEXT DEFAULT '',
            location        TEXT DEFAULT '',
            max_participants INTEGER DEFAULT 0,
            price           REAL DEFAULT 0,
            active          BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS media (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            title           TEXT DEFAULT '',
            media_type      TEXT DEFAULT 'photo',
            category        TEXT DEFAULT '',
            url             TEXT DEFAULT '',
            thumbnail       TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            belt_level      TEXT DEFAULT 'all',
            uploaded_by     INTEGER REFERENCES users(id),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bug_reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            report_type     TEXT DEFAULT 'bug',
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            screenshot      TEXT DEFAULT '',
            status          TEXT DEFAULT 'open',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            member_id       INTEGER REFERENCES members(id),
            notification_type TEXT DEFAULT 'general',
            title           TEXT DEFAULT '',
            message         TEXT DEFAULT '',
            read            BOOLEAN DEFAULT 0,
            sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1,
            subject         TEXT DEFAULT '',
            body            TEXT NOT NULL,
            channel         TEXT DEFAULT 'email',
            recipient_filter TEXT DEFAULT 'all',
            recipient_count INTEGER DEFAULT 0,
            total           INTEGER DEFAULT 0,
            delivered       INTEGER DEFAULT 0,
            opened          INTEGER DEFAULT 0,
            clicked         INTEGER DEFAULT 0,
            deferred        INTEGER DEFAULT 0,
            bounced         INTEGER DEFAULT 0,
            dropped         INTEGER DEFAULT 0,
            spam            INTEGER DEFAULT 0,
            sent_by         INTEGER REFERENCES users(id),
            status          TEXT DEFAULT 'sent',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS message_recipients (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            channel         TEXT DEFAULT 'email',
            status          TEXT DEFAULT 'sent',
            delivered_at    TIMESTAMP,
            opened_at       TIMESTAMP,
            clicked_at      TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_msg_recipients_msg ON message_recipients(message_id);
        CREATE INDEX IF NOT EXISTS idx_msg_recipients_member ON message_recipients(member_id);

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            user_name   TEXT DEFAULT '',
            action      TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id   INTEGER,
            details     TEXT DEFAULT '',
            ip_address  TEXT DEFAULT '',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );


        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_members_academy ON members(academy_id);
        CREATE INDEX IF NOT EXISTS idx_checkins_member ON check_ins(member_id, check_in_time DESC);
        CREATE INDEX IF NOT EXISTS idx_checkins_academy ON check_ins(academy_id, check_in_time DESC);
        CREATE INDEX IF NOT EXISTS idx_memberships_member ON memberships(member_id, start_date DESC);
        CREATE INDEX IF NOT EXISTS idx_payments_member ON payments(member_id);
        CREATE INDEX IF NOT EXISTS idx_payments_academy ON payments(academy_id);
    """)

    conn.commit()

    # ─── Seed Belt Ranks ────────────────────────────────────────
    all_belts = [
        # Kids belts
        ('White', '#FFFFFF', 1, 4, 0),
        ('Grey', '#808080', 2, 4, 0),
        ('Yellow', '#FFD700', 3, 4, 0),
        ('Orange', '#FF8C00', 4, 4, 0),
        ('Green', '#228B22', 5, 4, 0),
        # Adult belts
        ('Blue', '#0056B3', 6, 4, 24),
        ('Purple', '#6F42C1', 7, 4, 18),
        ('Brown', '#8B4513', 8, 4, 12),
        ('Black', '#000000', 9, 6, 24),
        # Coral/Red belts
        ('Red/Black', '#8B0000', 10, 0, 0),
        ('Red/White', '#DC143C', 11, 0, 0),
        ('Red', '#FF0000', 12, 0, 0),
    ]
    row = conn.execute("SELECT COUNT(*) as cnt FROM belt_ranks").fetchone()
    count = row['cnt'] if isinstance(row, dict) else row[0]
    if count == 0:
        for name, color, sort_order, max_stripes, min_months in all_belts:
            conn.execute(
                "INSERT INTO belt_ranks (name, color, sort_order, max_stripes, min_months) VALUES (?, ?, ?, ?, ?)",
                (name, color, sort_order, max_stripes, min_months)
            )
        print("[Seed] Belt ranks created")
    else:
        # Insert any missing belts (don't touch existing ones)
        for name, color, sort_order, max_stripes, min_months in all_belts:
            existing = conn.execute("SELECT id FROM belt_ranks WHERE name = ?", (name,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO belt_ranks (name, color, sort_order, max_stripes, min_months) VALUES (?, ?, ?, ?, ?)",
                    (name, color, sort_order, max_stripes, min_months)
                )
                print(f"[Seed] Added missing belt rank: {name}")
        # Update sort_order for existing belts to match IBJJF order
        for name, color, sort_order, max_stripes, min_months in all_belts:
            conn.execute(
                "UPDATE belt_ranks SET sort_order = ?, color = ?, max_stripes = ?, min_months = ? WHERE name = ?",
                (sort_order, color, max_stripes, min_months, name)
            )
    conn.commit()

    # ─── Seed Admin User ────────────────────────────────────────
    # ─── Add missing columns safely (PostgreSQL needs commit per ALTER) ─
    for alter in [
        "ALTER TABLE users ADD COLUMN photo_url TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN academy_id INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN trial_start TIMESTAMP",
        "ALTER TABLE academies ADD COLUMN logo_url TEXT DEFAULT ''",
        "ALTER TABLE messages ADD COLUMN total INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN delivered INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN opened INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN clicked INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN deferred INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN bounced INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN dropped INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN spam INTEGER DEFAULT 0",
        "ALTER TABLE members ADD COLUMN pin TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN webauthn_credential_id TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN webauthn_public_key TEXT DEFAULT ''",
        "ALTER TABLE prospects ADD COLUMN interested_in TEXT DEFAULT ''",
        "ALTER TABLE prospects ADD COLUMN member_id INTEGER",
    ]:
        try:
            conn.execute(alter)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # ─── Seed Admin User ──────────────────────────────────────
    try:
        row = conn.execute("SELECT id FROM users WHERE username = 'seeds13'").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users (username, password, name, email, role, active) VALUES (?, ?, ?, ?, ?, ?)",
                ('seeds13', _hash_password('Seeds2026!'), 'Seeds 13', '', 'admin', True)
            )
            conn.commit()
            print("[Seed] Admin user seeds13 created")
    except Exception as e:
        print(f"[Seed] Admin user error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # Try to update photo (may fail if column doesn't exist yet)
    try:
        conn.execute("UPDATE users SET photo_url = '/static/logo-seeds13-sm.png' WHERE username = 'seeds13'")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    # ─── Seed Default Academy ───────────────────────────────────
    try:
        row = conn.execute("SELECT id FROM academies WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO academies (name, owner_id) VALUES (?, ?)",
                ('Seeds 13 BJJ', 1)
            )
            conn.commit()
            print("[Seed] Default academy Seeds 13 BJJ created")
        # Try to set logo
        try:
            conn.execute("UPDATE academies SET logo_url = '/static/logo-seeds13-sm.png' WHERE id = 1")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    except Exception as e:
        print(f"[Seed] Academy error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    conn.commit()
    conn.close()
    print("[DB] Fit4Academy database initialized")


# ═══════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════

def authenticate_user(username, password):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    row = dict(row)
    if not row.get('active', True) in (True, 1):
        return None
    if _check_password(password, row['password']):
        return row
    return None


# ═══════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_user(username, password, name='', email='', phone='', role='user', academy_id=1):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password, name, email, phone, role, academy_id, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, _hash_password(password), name, email, phone, role, academy_id, True)
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id
    except Exception as e:
        print(f"[Users] Create error: {e}")
        conn.close()
        return None


def update_user(user_id, **kwargs):
    conn = get_db()
    allowed = ['username', 'name', 'email', 'phone', 'role', 'permissions', 'academy_id', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if 'password' in kwargs and kwargs['password']:
        fields.append("password = ?")
        values.append(_hash_password(kwargs['password']))
    if not fields:
        conn.close()
        return False
    values.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  ACADEMIES
# ═══════════════════════════════════════════════════════════════

def get_all_academies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM academies ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_academy_by_id(academy_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM academies WHERE id = ?", (academy_id,)).fetchone()
    conn.close()
    return row


def create_academy(name, owner_id, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO academies (name, owner_id, logo, address, city, state, zip_code, country,
           phone, email, website, timezone, currency, language, theme)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, owner_id, kwargs.get('logo', ''), kwargs.get('address', ''),
         kwargs.get('city', ''), kwargs.get('state', ''), kwargs.get('zip_code', ''),
         kwargs.get('country', 'United States'), kwargs.get('phone', ''),
         kwargs.get('email', ''), kwargs.get('website', ''),
         kwargs.get('timezone', 'America/Denver'), kwargs.get('currency', 'USD'),
         kwargs.get('language', 'en'), kwargs.get('theme', 'dark'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_academy(academy_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'logo', 'address', 'city', 'state', 'zip_code', 'country',
               'phone', 'email', 'website', 'timezone', 'currency', 'language', 'theme']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(academy_id)
    conn.execute(f"UPDATE academies SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_academy(academy_id):
    conn = get_db()
    conn.execute("DELETE FROM academies WHERE id = ?", (academy_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  MEMBERS
# ═══════════════════════════════════════════════════════════════

def get_all_members(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT m.*, b.name as belt_name, b.color as belt_color
           FROM members m
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           WHERE m.academy_id = ?
           ORDER BY m.last_name, m.first_name""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_members_enriched(academy_id=1):
    """Get all members with membership and last check-in in a single query."""
    conn = get_db()
    rows = conn.execute(
        """SELECT m.*, b.name as belt_name, b.color as belt_color,
                  mp.name as plan_name, mp.id as plan_id,
                  ms_sub.end_date as ms_end_date,
                  ci_sub.last_checkin
           FROM members m
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           LEFT JOIN (
               SELECT ms.member_id, ms.plan_id, ms.end_date,
                      ROW_NUMBER() OVER (PARTITION BY ms.member_id ORDER BY ms.start_date DESC) as rn
               FROM memberships ms
           ) ms_sub ON ms_sub.member_id = m.id AND ms_sub.rn = 1
           LEFT JOIN membership_plans mp ON ms_sub.plan_id = mp.id
           LEFT JOIN (
               SELECT member_id, MAX(check_in_time) as last_checkin
               FROM check_ins
               GROUP BY member_id
           ) ci_sub ON ci_sub.member_id = m.id
           WHERE m.academy_id = ?
           ORDER BY m.last_name, m.first_name""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_member_by_id(member_id):
    conn = get_db()
    row = conn.execute(
        """SELECT m.*, b.name as belt_name, b.color as belt_color
           FROM members m
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           WHERE m.id = ?""",
        (member_id,)
    ).fetchone()
    conn.close()
    return row


def _generate_pin():
    """Generate a unique 4-digit PIN."""
    import random
    return str(random.randint(1000, 9999))


def create_member(academy_id=1, **kwargs):
    conn = get_db()
    pin = kwargs.get('pin', '') or _generate_pin()
    cur = conn.execute(
        """INSERT INTO members (academy_id, first_name, last_name, email, phone,
           date_of_birth, gender, belt_rank_id, stripes, membership_status,
           join_date, emergency_contact, emergency_phone, medical_notes, photo,
           pin, qr_code, source, notes, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('first_name', ''), kwargs.get('last_name', ''),
         kwargs.get('email', ''), kwargs.get('phone', ''),
         kwargs.get('date_of_birth'), kwargs.get('gender', ''),
         kwargs.get('belt_rank_id', 1), kwargs.get('stripes', 0),
         kwargs.get('membership_status', 'active'), kwargs.get('join_date', str(date.today())),
         kwargs.get('emergency_contact', ''), kwargs.get('emergency_phone', ''),
         kwargs.get('medical_notes', ''), kwargs.get('photo', ''),
         pin, kwargs.get('qr_code', ''), kwargs.get('source', ''),
         kwargs.get('notes', ''), True)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_member(member_id, **kwargs):
    conn = get_db()
    allowed = ['first_name', 'last_name', 'email', 'phone', 'date_of_birth',
               'gender', 'belt_rank_id', 'stripes', 'membership_status', 'join_date',
               'emergency_contact', 'emergency_phone', 'medical_notes', 'photo',
               'pin', 'qr_code', 'source', 'notes', 'active',
               'webauthn_credential_id', 'webauthn_public_key']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    if not fields:
        conn.close()
        return False
    values.append(member_id)
    conn.execute(f"UPDATE members SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_member(member_id):
    conn = get_db()
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    return True


def search_members(query, academy_id=1):
    conn = get_db()
    search = f"%{query}%"
    rows = conn.execute(
        """SELECT m.*, b.name as belt_name, b.color as belt_color
           FROM members m
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           WHERE m.academy_id = ?
             AND (m.first_name LIKE ? OR m.last_name LIKE ? OR m.email LIKE ? OR m.phone LIKE ?)
           ORDER BY m.last_name, m.first_name""",
        (academy_id, search, search, search, search)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP PLANS
# ═══════════════════════════════════════════════════════════════

def get_all_membership_plans(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM membership_plans WHERE academy_id = ? ORDER BY price",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_membership_plan_by_id(plan_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM membership_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return row


def create_membership_plan(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO membership_plans (academy_id, name, plan_type, price, billing_cycle,
           trial_days, description, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('name', ''), kwargs.get('plan_type', 'monthly'),
         kwargs.get('price', 0), kwargs.get('billing_cycle', 'monthly'),
         kwargs.get('trial_days', 0), kwargs.get('description', ''), True)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_membership_plan(plan_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'plan_type', 'price', 'billing_cycle', 'trial_days', 'description', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(plan_id)
    conn.execute(f"UPDATE membership_plans SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_membership_plan(plan_id):
    conn = get_db()
    conn.execute("DELETE FROM membership_plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIPS
# ═══════════════════════════════════════════════════════════════

def get_all_memberships(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT ms.*, m.first_name, m.last_name, mp.name as plan_name, mp.price
           FROM memberships ms
           JOIN members m ON ms.member_id = m.id
           LEFT JOIN membership_plans mp ON ms.plan_id = mp.id
           WHERE m.academy_id = ?
           ORDER BY ms.start_date DESC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_membership_by_id(membership_id):
    conn = get_db()
    row = conn.execute(
        """SELECT ms.*, m.first_name, m.last_name, mp.name as plan_name
           FROM memberships ms
           JOIN members m ON ms.member_id = m.id
           LEFT JOIN membership_plans mp ON ms.plan_id = mp.id
           WHERE ms.id = ?""",
        (membership_id,)
    ).fetchone()
    conn.close()
    return row


def get_memberships_by_member(member_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT ms.*, mp.name as plan_name, mp.price
           FROM memberships ms
           LEFT JOIN membership_plans mp ON ms.plan_id = mp.id
           WHERE ms.member_id = ?
           ORDER BY ms.start_date DESC""",
        (member_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_membership(member_id, plan_id, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO memberships (member_id, plan_id, status, start_date, end_date, auto_renew)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (member_id, plan_id, kwargs.get('status', 'active'),
         kwargs.get('start_date', str(date.today())), kwargs.get('end_date'),
         kwargs.get('auto_renew', True))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_membership(membership_id, **kwargs):
    conn = get_db()
    allowed = ['plan_id', 'status', 'start_date', 'end_date', 'auto_renew']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(membership_id)
    conn.execute(f"UPDATE memberships SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_membership(membership_id):
    conn = get_db()
    conn.execute("DELETE FROM memberships WHERE id = ?", (membership_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  CLASSES
# ═══════════════════════════════════════════════════════════════

def get_all_classes(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM classes WHERE academy_id = ? ORDER BY name",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_class_by_id(class_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    conn.close()
    return row


def create_class(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO classes (academy_id, name, class_type, instructor, description,
           duration, max_capacity, belt_level, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('name', ''), kwargs.get('class_type', 'gi'),
         kwargs.get('instructor', ''), kwargs.get('description', ''),
         kwargs.get('duration', 60), kwargs.get('max_capacity', 30),
         kwargs.get('belt_level', 'all'), True)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_class(class_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'class_type', 'instructor', 'description', 'duration',
               'max_capacity', 'belt_level', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(class_id)
    conn.execute(f"UPDATE classes SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_class(class_id):
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  CLASS SCHEDULE
# ═══════════════════════════════════════════════════════════════

def get_all_class_schedules(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT cs.*, c.name as class_name, c.class_type, c.instructor
           FROM class_schedule cs
           JOIN classes c ON cs.class_id = c.id
           WHERE c.academy_id = ?
           ORDER BY cs.day_of_week, cs.start_time""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_class_schedule_by_id(schedule_id):
    conn = get_db()
    row = conn.execute(
        """SELECT cs.*, c.name as class_name
           FROM class_schedule cs
           JOIN classes c ON cs.class_id = c.id
           WHERE cs.id = ?""",
        (schedule_id,)
    ).fetchone()
    conn.close()
    return row


def get_schedule_by_day(day_of_week, academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT cs.*, c.name as class_name, c.class_type, c.instructor, c.duration
           FROM class_schedule cs
           JOIN classes c ON cs.class_id = c.id
           WHERE cs.day_of_week = ? AND c.academy_id = ? AND cs.active = ?
           ORDER BY cs.start_time""",
        (day_of_week, academy_id, True)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedules_for_class(class_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM class_schedule WHERE class_id = ? ORDER BY day_of_week",
        (class_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_class_schedules(class_id):
    conn = get_db()
    conn.execute("DELETE FROM class_schedule WHERE class_id = ?", (class_id,))
    conn.commit()
    conn.close()


def create_class_schedule(class_id, day_of_week, start_time, end_time):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO class_schedule (class_id, day_of_week, start_time, end_time, active) VALUES (?, ?, ?, ?, ?)",
        (class_id, day_of_week, start_time, end_time, True)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_class_schedule(schedule_id, **kwargs):
    conn = get_db()
    allowed = ['class_id', 'day_of_week', 'start_time', 'end_time', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(schedule_id)
    conn.execute(f"UPDATE class_schedule SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_class_schedule(schedule_id):
    conn = get_db()
    conn.execute("DELETE FROM class_schedule WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  CHECK-INS
# ═══════════════════════════════════════════════════════════════

def get_all_checkins(academy_id=1, limit=100):
    conn = get_db()
    rows = conn.execute(
        """SELECT ci.*, m.first_name, m.last_name, m.photo,
                  b.name as belt_name, b.color as belt_color,
                  c.name as class_name
           FROM check_ins ci
           JOIN members m ON ci.member_id = m.id
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           LEFT JOIN classes c ON ci.class_id = c.id
           WHERE ci.academy_id = ?
           ORDER BY ci.check_in_time DESC
           LIMIT ?""",
        (academy_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_checkin_by_id(checkin_id):
    conn = get_db()
    row = conn.execute(
        """SELECT ci.*, m.first_name, m.last_name
           FROM check_ins ci
           JOIN members m ON ci.member_id = m.id
           WHERE ci.id = ?""",
        (checkin_id,)
    ).fetchone()
    conn.close()
    return row


def get_checkins_by_member(member_id, limit=50):
    conn = get_db()
    rows = conn.execute(
        """SELECT ci.*, c.name as class_name
           FROM check_ins ci
           LEFT JOIN classes c ON ci.class_id = c.id
           WHERE ci.member_id = ?
           ORDER BY ci.check_in_time DESC
           LIMIT ?""",
        (member_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_checkin(member_id, class_id=None, academy_id=1, method='manual'):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO check_ins (member_id, class_id, academy_id, method) VALUES (?, ?, ?, ?)",
        (member_id, class_id, academy_id, method)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_checkin(checkin_id):
    conn = get_db()
    conn.execute("DELETE FROM check_ins WHERE id = ?", (checkin_id,))
    conn.commit()
    conn.close()
    return True


def get_today_checkins(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT ci.*, m.first_name, m.last_name, m.photo,
                  b.name as belt_name, b.color as belt_color,
                  c.name as class_name
           FROM check_ins ci
           JOIN members m ON ci.member_id = m.id
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           LEFT JOIN classes c ON ci.class_id = c.id
           WHERE ci.academy_id = ? AND DATE(ci.check_in_time) = date('now')
           ORDER BY ci.check_in_time DESC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  BELT RANKS
# ═══════════════════════════════════════════════════════════════

def get_all_belt_ranks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM belt_ranks ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_belt_rank_by_id(belt_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM belt_ranks WHERE id = ?", (belt_id,)).fetchone()
    conn.close()
    return row


def create_belt_rank(name, color, sort_order=0, max_stripes=4, min_months=0):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO belt_ranks (name, color, sort_order, max_stripes, min_months) VALUES (?, ?, ?, ?, ?)",
        (name, color, sort_order, max_stripes, min_months)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_belt_rank(belt_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'color', 'sort_order', 'max_stripes', 'min_months']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(belt_id)
    conn.execute(f"UPDATE belt_ranks SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_belt_rank(belt_id):
    conn = get_db()
    conn.execute("DELETE FROM belt_ranks WHERE id = ?", (belt_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  PROMOTIONS
# ═══════════════════════════════════════════════════════════════

def get_all_promotions(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.*, m.first_name, m.last_name,
                  fb.name as from_belt_name, fb.color as from_belt_color,
                  tb.name as to_belt_name, tb.color as to_belt_color
           FROM promotions p
           JOIN members m ON p.member_id = m.id
           LEFT JOIN belt_ranks fb ON p.from_belt_id = fb.id
           LEFT JOIN belt_ranks tb ON p.to_belt_id = tb.id
           WHERE m.academy_id = ?
           ORDER BY p.promotion_date DESC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_promotion_by_id(promotion_id):
    conn = get_db()
    row = conn.execute(
        """SELECT p.*, m.first_name, m.last_name,
                  fb.name as from_belt_name, tb.name as to_belt_name
           FROM promotions p
           JOIN members m ON p.member_id = m.id
           LEFT JOIN belt_ranks fb ON p.from_belt_id = fb.id
           LEFT JOIN belt_ranks tb ON p.to_belt_id = tb.id
           WHERE p.id = ?""",
        (promotion_id,)
    ).fetchone()
    conn.close()
    return row


def get_promotions_by_member(member_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.*, fb.name as from_belt_name, fb.color as from_belt_color,
                  tb.name as to_belt_name, tb.color as to_belt_color
           FROM promotions p
           LEFT JOIN belt_ranks fb ON p.from_belt_id = fb.id
           LEFT JOIN belt_ranks tb ON p.to_belt_id = tb.id
           WHERE p.member_id = ?
           ORDER BY p.promotion_date DESC""",
        (member_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_promotion(member_id, from_belt_id, to_belt_id, from_stripes=0, to_stripes=0, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO promotions (member_id, from_belt_id, to_belt_id, from_stripes, to_stripes,
           promotion_date, promoted_by, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (member_id, from_belt_id, to_belt_id, from_stripes, to_stripes,
         kwargs.get('promotion_date', str(date.today())),
         kwargs.get('promoted_by', ''), kwargs.get('notes', ''))
    )
    # Update the member's belt
    conn.execute(
        "UPDATE members SET belt_rank_id = ?, stripes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (to_belt_id, to_stripes, member_id)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_promotion(promotion_id, **kwargs):
    conn = get_db()
    allowed = ['from_belt_id', 'to_belt_id', 'from_stripes', 'to_stripes',
               'promotion_date', 'promoted_by', 'notes']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(promotion_id)
    conn.execute(f"UPDATE promotions SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_promotion(promotion_id):
    conn = get_db()
    conn.execute("DELETE FROM promotions WHERE id = ?", (promotion_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  PAYMENTS
# ═══════════════════════════════════════════════════════════════

def get_all_payments(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.*, m.first_name, m.last_name
           FROM payments p
           JOIN members m ON p.member_id = m.id
           WHERE p.academy_id = ?
           ORDER BY p.payment_date DESC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment_by_id(payment_id):
    conn = get_db()
    row = conn.execute(
        """SELECT p.*, m.first_name, m.last_name
           FROM payments p
           JOIN members m ON p.member_id = m.id
           WHERE p.id = ?""",
        (payment_id,)
    ).fetchone()
    conn.close()
    return row


def get_payments_by_member(member_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM payments WHERE member_id = ? ORDER BY payment_date DESC",
        (member_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_payment(member_id, amount, academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO payments (member_id, academy_id, membership_id, amount, method,
           status, reference, notes, payment_date, due_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (member_id, academy_id, kwargs.get('membership_id'),
         amount, kwargs.get('method', 'cash'),
         kwargs.get('status', 'completed'), kwargs.get('reference', ''),
         kwargs.get('notes', ''), kwargs.get('payment_date', str(date.today())),
         kwargs.get('due_date'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_payment(payment_id, **kwargs):
    conn = get_db()
    allowed = ['amount', 'method', 'status', 'reference', 'notes', 'payment_date', 'due_date']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(payment_id)
    conn.execute(f"UPDATE payments SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_payment(payment_id):
    conn = get_db()
    conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return True


def get_payment_alerts(academy_id=1):
    """Get overdue and upcoming due payments."""
    conn = get_db()
    rows = conn.execute(
        """SELECT p.*, m.first_name, m.last_name
           FROM payments p
           JOIN members m ON p.member_id = m.id
           WHERE p.academy_id = ?
             AND p.status IN ('pending', 'overdue')
             AND p.due_date IS NOT NULL
           ORDER BY p.due_date ASC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  PAYMENT METHODS
# ═══════════════════════════════════════════════════════════════

def get_all_payment_methods(member_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM payment_methods WHERE member_id = ? ORDER BY is_default DESC",
        (member_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment_method_by_id(pm_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM payment_methods WHERE id = ?", (pm_id,)).fetchone()
    conn.close()
    return row


def create_payment_method(member_id, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO payment_methods (member_id, method_type, last4, brand, stripe_pm_id, is_default)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (member_id, kwargs.get('method_type', 'credit_card'),
         kwargs.get('last4', ''), kwargs.get('brand', ''),
         kwargs.get('stripe_pm_id', ''), kwargs.get('is_default', False))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_payment_method(pm_id, **kwargs):
    conn = get_db()
    allowed = ['method_type', 'last4', 'brand', 'stripe_pm_id', 'is_default']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(pm_id)
    conn.execute(f"UPDATE payment_methods SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_payment_method(pm_id):
    conn = get_db()
    conn.execute("DELETE FROM payment_methods WHERE id = ?", (pm_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  PROSPECTS
# ═══════════════════════════════════════════════════════════════

def get_all_prospects(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM prospects WHERE academy_id = ? ORDER BY created_at DESC",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prospect_by_id(prospect_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
    conn.close()
    return row


def create_prospect(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO prospects (academy_id, first_name, last_name, email, phone,
           source, status, interested_in, member_id, follow_up_date, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('first_name', ''), kwargs.get('last_name', ''),
         kwargs.get('email', ''), kwargs.get('phone', ''),
         kwargs.get('source', ''), kwargs.get('status', 'new'),
         kwargs.get('interested_in', ''), kwargs.get('member_id'),
         kwargs.get('follow_up_date'), kwargs.get('notes', ''))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_prospect(prospect_id, **kwargs):
    conn = get_db()
    allowed = ['first_name', 'last_name', 'email', 'phone', 'source',
               'status', 'follow_up_date', 'notes']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    if not fields:
        conn.close()
        return False
    values.append(prospect_id)
    conn.execute(f"UPDATE prospects SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_prospect(prospect_id):
    conn = get_db()
    conn.execute("DELETE FROM prospects WHERE id = ?", (prospect_id,))
    conn.commit()
    conn.close()
    return True


def convert_prospect_to_member(prospect_id, academy_id=1):
    """Convert a prospect to a member."""
    prospect = get_prospect_by_id(prospect_id)
    if not prospect:
        return None
    member_id = create_member(
        academy_id=academy_id,
        first_name=prospect['first_name'],
        last_name=prospect.get('last_name', ''),
        email=prospect.get('email', ''),
        phone=prospect.get('phone', ''),
        source=prospect.get('source', 'prospect')
    )
    if member_id:
        update_prospect(prospect_id, status='converted')
    return member_id


# ═══════════════════════════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════════════════════════

def get_all_events(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM events WHERE academy_id = ? ORDER BY event_date DESC",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_event_by_id(event_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return row


def get_upcoming_events(academy_id=1, limit=10):
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM events
           WHERE academy_id = ? AND event_date >= date('now') AND active = ?
           ORDER BY event_date ASC
           LIMIT ?""",
        (academy_id, True, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_event(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO events (academy_id, name, event_type, description, event_date,
           start_time, end_time, location, max_participants, price, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('name', ''), kwargs.get('event_type', 'seminar'),
         kwargs.get('description', ''), kwargs.get('event_date'),
         kwargs.get('start_time', ''), kwargs.get('end_time', ''),
         kwargs.get('location', ''), kwargs.get('max_participants', 0),
         kwargs.get('price', 0), True)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_event(event_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'event_type', 'description', 'event_date', 'start_time',
               'end_time', 'location', 'max_participants', 'price', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(event_id)
    conn.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_event(event_id):
    conn = get_db()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  MEDIA
# ═══════════════════════════════════════════════════════════════

def get_all_media(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM media WHERE academy_id = ? ORDER BY created_at DESC",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_media_by_id(media_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    conn.close()
    return row


def get_media_by_category(category, academy_id=1):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM media WHERE academy_id = ? AND category = ? ORDER BY created_at DESC",
        (academy_id, category)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_media(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO media (academy_id, title, media_type, category, url, thumbnail,
           description, belt_level, uploaded_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('title', ''), kwargs.get('media_type', 'photo'),
         kwargs.get('category', ''), kwargs.get('url', ''),
         kwargs.get('thumbnail', ''), kwargs.get('description', ''),
         kwargs.get('belt_level', 'all'), kwargs.get('uploaded_by'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_media(media_id, **kwargs):
    conn = get_db()
    allowed = ['title', 'media_type', 'category', 'url', 'thumbnail',
               'description', 'belt_level']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(media_id)
    conn.execute(f"UPDATE media SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_media(media_id):
    conn = get_db()
    conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  BUG REPORTS
# ═══════════════════════════════════════════════════════════════

def get_all_bug_reports():
    conn = get_db()
    rows = conn.execute(
        """SELECT br.*, u.name as user_name
           FROM bug_reports br
           LEFT JOIN users u ON br.user_id = u.id
           ORDER BY br.created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bug_report_by_id(report_id):
    conn = get_db()
    row = conn.execute(
        """SELECT br.*, u.name as user_name
           FROM bug_reports br
           LEFT JOIN users u ON br.user_id = u.id
           WHERE br.id = ?""",
        (report_id,)
    ).fetchone()
    conn.close()
    return row


def create_bug_report(user_id, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO bug_reports (user_id, report_type, title, description, screenshot, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, kwargs.get('report_type', 'bug'), kwargs.get('title', ''),
         kwargs.get('description', ''), kwargs.get('screenshot', ''), 'open')
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_bug_report(report_id, **kwargs):
    conn = get_db()
    allowed = ['report_type', 'title', 'description', 'screenshot', 'status']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(report_id)
    conn.execute(f"UPDATE bug_reports SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_bug_report(report_id):
    conn = get_db()
    conn.execute("DELETE FROM bug_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def get_all_notifications(academy_id=1, limit=50):
    conn = get_db()
    rows = conn.execute(
        """SELECT n.*, m.first_name, m.last_name
           FROM notifications n
           LEFT JOIN members m ON n.member_id = m.id
           WHERE n.academy_id = ?
           ORDER BY n.created_at DESC
           LIMIT ?""",
        (academy_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_notification_by_id(notif_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,)).fetchone()
    conn.close()
    return row


def get_unread_notifications(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT n.*, m.first_name, m.last_name
           FROM notifications n
           LEFT JOIN members m ON n.member_id = m.id
           WHERE n.academy_id = ? AND n.read = ?
           ORDER BY n.created_at DESC""",
        (academy_id, False)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_notification(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO notifications (academy_id, member_id, notification_type, title, message)
           VALUES (?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('member_id'), kwargs.get('notification_type', 'general'),
         kwargs.get('title', ''), kwargs.get('message', ''))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_notification(notif_id, **kwargs):
    conn = get_db()
    allowed = ['title', 'message', 'read', 'notification_type']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(notif_id)
    conn.execute(f"UPDATE notifications SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def mark_notification_read(notif_id):
    return update_notification(notif_id, read=True)


def delete_notification(notif_id):
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  MESSAGES (Mass Communication)
# ═══════════════════════════════════════════════════════════════

def create_message(academy_id=1, **kwargs):
    conn = get_db()
    total = kwargs.get('recipient_count', 0)
    cur = conn.execute(
        """INSERT INTO messages (academy_id, subject, body, channel, recipient_filter,
           recipient_count, total, delivered, sent_by, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('subject', ''), kwargs.get('body', ''),
         kwargs.get('channel', 'email'), kwargs.get('recipient_filter', 'all'),
         total, total, kwargs.get('delivered', total),
         kwargs.get('sent_by'), kwargs.get('status', 'sent'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_messaging_stats(academy_id=1):
    """Get aggregate messaging stats across all messages."""
    conn = get_db()
    row = conn.execute(
        """SELECT
            COUNT(*) as total_messages,
            COALESCE(SUM(total), 0) as total_sent,
            COALESCE(SUM(CASE WHEN channel = 'email' THEN total ELSE 0 END), 0) as total_email,
            COALESCE(SUM(CASE WHEN channel = 'sms' THEN total ELSE 0 END), 0) as total_sms,
            COALESCE(SUM(CASE WHEN channel = 'both' THEN total ELSE 0 END), 0) as total_both,
            COALESCE(SUM(delivered), 0) as delivered,
            COALESCE(SUM(opened), 0) as opened,
            COALESCE(SUM(clicked), 0) as clicked,
            COALESCE(SUM(deferred), 0) as deferred,
            COALESCE(SUM(bounced), 0) as bounced,
            COALESCE(SUM(dropped), 0) as dropped,
            COALESCE(SUM(spam), 0) as spam
           FROM messages WHERE academy_id = ?""",
        (academy_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def update_message_stats(message_id, **kwargs):
    """Update delivery stats on a message."""
    conn = get_db()
    allowed = ['total', 'delivered', 'opened', 'clicked', 'deferred', 'bounced', 'dropped', 'spam', 'status']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if fields:
        values.append(message_id)
        conn.execute(f"UPDATE messages SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def get_all_messages(academy_id=1, limit=50):
    conn = get_db()
    rows = conn.execute(
        """SELECT msg.*, u.name as sent_by_name
           FROM messages msg
           LEFT JOIN users u ON msg.sent_by = u.id
           WHERE msg.academy_id = ?
           ORDER BY msg.created_at DESC
           LIMIT ?""",
        (academy_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_members_by_filter(academy_id=1, filter_type='all', filter_value=''):
    """Get members matching a filter for messaging."""
    conn = get_db()
    if filter_type == 'status':
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               WHERE m.academy_id = ? AND m.membership_status = ? AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id, filter_value)
        ).fetchall()
    elif filter_type == 'belt':
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
               WHERE m.academy_id = ? AND LOWER(b.name) = LOWER(?) AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id, filter_value)
        ).fetchall()
    elif filter_type == 'plan':
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               JOIN memberships ms ON ms.member_id = m.id
               WHERE m.academy_id = ? AND ms.plan_id = ? AND ms.status = 'active' AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id, filter_value)
        ).fetchall()
    elif filter_type == 'manual':
        if not filter_value:
            conn.close()
            return []
        ids = [int(x) for x in filter_value.split(',') if x.strip().isdigit()]
        if not ids:
            conn.close()
            return []
        placeholders = ','.join('?' * len(ids))
        rows = conn.execute(
            f"""SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               WHERE m.academy_id = ? AND m.id IN ({placeholders}) AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            [academy_id] + ids
        ).fetchall()
    else:  # 'all'
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               WHERE m.academy_id = ? AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  AUDIT LOG
# ═══════════════════════════════════════════════════════════════

def get_audit_log(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_audit_entry(user_id, user_name, action, entity_type, entity_id=None, details='', ip_address=''):
    conn = get_db()
    conn.execute(
        """INSERT INTO audit_log (user_id, user_name, action, entity_type, entity_id, details, ip_address)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, user_name, action, entity_type, entity_id, details, ip_address)
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD & ANALYTICS
# ═══════════════════════════════════════════════════════════════

def get_dashboard_stats(academy_id=1):
    conn = get_db()
    stats = {}

    # Active members
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM members WHERE academy_id = ? AND membership_status = 'active' AND active = ?",
        (academy_id, True)
    ).fetchone()
    stats['active_members'] = row['cnt'] if isinstance(row, dict) else row[0]

    # Total members
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM members WHERE academy_id = ?",
        (academy_id,)
    ).fetchone()
    stats['total_members'] = row['cnt'] if isinstance(row, dict) else row[0]

    # Today check-ins
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM check_ins WHERE academy_id = ? AND DATE(check_in_time) = date('now')",
        (academy_id,)
    ).fetchone()
    stats['today_checkins'] = row['cnt'] if isinstance(row, dict) else row[0]

    # Monthly revenue
    row = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) as total FROM payments
           WHERE academy_id = ? AND status = 'completed'
           AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')""",
        (academy_id,)
    ).fetchone()
    stats['monthly_revenue'] = row['total'] if isinstance(row, dict) else row[0]

    # Expiring memberships (next 30 days)
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM memberships ms
           JOIN members m ON ms.member_id = m.id
           WHERE m.academy_id = ? AND ms.status = 'active'
           AND ms.end_date IS NOT NULL
           AND ms.end_date BETWEEN date('now') AND date('now', '+30 days')""",
        (academy_id,)
    ).fetchone()
    stats['expiring_soon'] = row['cnt'] if isinstance(row, dict) else row[0]

    # Prospects count
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM prospects WHERE academy_id = ? AND status NOT IN ('converted', 'lost')",
        (academy_id,)
    ).fetchone()
    stats['active_prospects'] = row['cnt'] if isinstance(row, dict) else row[0]

    conn.close()
    return stats


def get_upcoming_birthdays(academy_id=1, days=30):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, first_name, last_name, date_of_birth, photo
           FROM members
           WHERE academy_id = ? AND date_of_birth IS NOT NULL AND date_of_birth != ''
           AND active = ?
           ORDER BY substr(date_of_birth, 6)""",
        (academy_id, True)
    ).fetchall()
    conn.close()
    # Filter in Python for cross-DB compatibility
    upcoming = []
    today = date.today()
    for m in rows:
        dob = m.get('date_of_birth', '') if isinstance(m, dict) else ''
        if not dob:
            continue
        try:
            bday = datetime.strptime(str(dob)[:10], '%Y-%m-%d').date()
            next_bday = bday.replace(year=today.year)
            if next_bday < today:
                next_bday = next_bday.replace(year=today.year + 1)
            diff = (next_bday - today).days
            if diff <= days:
                entry = dict(m) if not isinstance(m, dict) else m
                entry['days_until'] = diff
                upcoming.append(entry)
        except Exception:
            continue
    upcoming.sort(key=lambda x: x.get('days_until', 999))
    return upcoming


def get_expiring_memberships(academy_id=1, days=30):
    conn = get_db()
    rows = conn.execute(
        """SELECT ms.*, m.first_name, m.last_name, m.email, m.phone, mp.name as plan_name
           FROM memberships ms
           JOIN members m ON ms.member_id = m.id
           LEFT JOIN membership_plans mp ON ms.plan_id = mp.id
           WHERE m.academy_id = ? AND ms.status = 'active'
           AND ms.end_date IS NOT NULL
           AND ms.end_date BETWEEN date('now') AND date('now', '+30 days')
           ORDER BY ms.end_date ASC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_belt_distribution(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT b.name, b.color_hex as color, b.sort_order, COUNT(m.id) as count
           FROM belt_ranks b
           LEFT JOIN members m ON m.belt_rank = b.name AND m.academy_id = ? AND m.active = 1
           WHERE b.academy_id = ?
           GROUP BY b.id, b.name, b.color_hex, b.sort_order
           ORDER BY b.sort_order""",
        (academy_id, academy_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_member_streak(member_id):
    """Calculate weekly training streak for a member."""
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT date(check_in_time) as checkin_date
           FROM check_ins
           WHERE member_id = ?
           ORDER BY check_in_time DESC
           LIMIT 90""",
        (member_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    dates = set()
    for r in rows:
        d = str(r.get('checkin_date', '') if isinstance(r, dict) else r[0])[:10]
        if d:
            dates.add(d)

    # Count consecutive weeks with at least 1 training
    from datetime import datetime, timedelta
    today = datetime.now().date()
    streak = 0

    for week_offset in range(52):  # Check up to 52 weeks back
        week_start = today - timedelta(days=today.weekday() + 7 * week_offset)
        week_end = week_start + timedelta(days=6)

        week_dates = [d for d in dates if week_start.isoformat() <= d <= week_end.isoformat()]
        if week_dates:
            streak += 1
        else:
            break

    return streak


def get_at_risk_members(academy_id=1, days_threshold=7):
    """Get active members who haven't checked in for X days."""
    conn = get_db()
    rows = conn.execute(
        """SELECT m.id, m.first_name, m.last_name, m.email, m.phone, m.belt_rank_id,
                  MAX(ci.check_in_time) as last_checkin,
                  CAST(julianday('now') - julianday(MAX(ci.check_in_time)) AS INTEGER) as days_absent
           FROM members m
           LEFT JOIN check_ins ci ON ci.member_id = m.id
           WHERE m.academy_id = ? AND m.membership_status = 'active'
           GROUP BY m.id
           HAVING days_absent >= ? OR last_checkin IS NULL
           ORDER BY days_absent DESC""",
        (academy_id, days_threshold)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_checkin_count(academy_id=1):
    """Get total check-ins for today."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM check_ins WHERE academy_id = ? AND date(check_in_time) = date('now')",
        (academy_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


def get_monthly_revenue(academy_id=1, months=12):
    conn = get_db()
    rows = conn.execute(
        """SELECT strftime('%Y-%m', payment_date) as month,
                  SUM(amount) as total,
                  COUNT(*) as count
           FROM payments
           WHERE academy_id = ? AND status = 'completed'
           GROUP BY strftime('%Y-%m', payment_date)
           ORDER BY month DESC
           LIMIT ?""",
        (academy_id, months)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_revenue_by_method(academy_id=1):
    conn = get_db()
    rows = conn.execute(
        """SELECT method, SUM(amount) as total, COUNT(*) as count
           FROM payments
           WHERE academy_id = ? AND status = 'completed'
           AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
           GROUP BY method
           ORDER BY total DESC""",
        (academy_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
