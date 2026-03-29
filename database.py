"""Database abstraction — SQLite locally, PostgreSQL on Railway.
Drop-in replacement: returns a connection that behaves like sqlite3."""

import os
import sqlite3

def _get_database_url():
    # Try multiple env var names
    url = os.getenv('DATABASE_URL', '')
    if not url:
        url = os.getenv('DATABASE_PUBLIC_URL', '')
    if not url:
        url = os.getenv('POSTGRES_URL', '')
    if not url:
        # Build from individual PG vars
        pghost = os.getenv('PGHOST', '')
        pgport = os.getenv('PGPORT', '5432')
        pguser = os.getenv('PGUSER', 'postgres')
        pgpass = os.getenv('PGPASSWORD', '')
        pgdb = os.getenv('PGDATABASE', 'railway')
        if pghost and pgpass:
            url = f'postgresql://{pguser}:{pgpass}@{pghost}:{pgport}/{pgdb}'
    if not url:
        from railway_config import IS_RAILWAY, RAILWAY_DATABASE_URL
        if IS_RAILWAY:
            url = RAILWAY_DATABASE_URL
    # Last resort fallback for Railway
    if not url and bool(os.getenv('RAILWAY_ENVIRONMENT')):
        url = 'postgresql://postgres:CVZWuWARcAdzxVPdJxcKITadIAnxxUJK@ballast.proxy.rlwy.net:12466/railway'
        print("[DB] Using hardcoded Railway PostgreSQL URL (env vars not found)")
    if url:
        print(f"[DB] URL found: {url[:40]}...")
    else:
        print("[DB] WARNING: No database URL found!")
    return url


def get_connection():
    """Return a database connection that works like sqlite3."""
    db_url = _get_database_url()
    if db_url:
        return _pg_connect(db_url)
    else:
        return _sqlite_connect()


def _sqlite_connect():
    from config import DATABASE_PATH
    db_dir = os.path.dirname(os.path.abspath(DATABASE_PATH))
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _pg_connect(db_url):
    """Wrap psycopg2 to behave exactly like sqlite3."""
    import psycopg2
    import psycopg2.extras
    raw = psycopg2.connect(db_url)
    return PGConnection(raw)


class PGConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        is_insert = sql.strip().upper().startswith('INSERT')
        is_select = sql.strip().upper().startswith('SELECT')
        sql = _convert_sql(sql)
        cur = self._conn.cursor(cursor_factory=__import__('psycopg2').extras.RealDictCursor)
        try:
            cur.execute(sql, params or ())
        except Exception as e:
            try:
                self._conn.rollback()
            except Exception:
                pass
            print(f"[PG] Query error: {e}")
            raise e
        return PGCursor(cur, is_insert=is_insert)

    def executescript(self, sql):
        """Execute multiple CREATE TABLE statements. SAFE: blocks destructive operations."""
        self._conn.autocommit = True
        cur = self._conn.cursor()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if not stmt:
                continue
            # SAFETY: Block destructive statements
            upper = stmt.upper().lstrip()
            if any(upper.startswith(kw) for kw in ['DROP ', 'TRUNCATE ', 'DELETE FROM']):
                print(f"[DB SAFETY] BLOCKED destructive statement: {stmt[:80]}")
                continue
            stmt = _convert_sql(stmt)
            stmt = stmt.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            try:
                cur.execute(stmt)
            except Exception as e:
                # Log but don't crash — table likely already exists
                if 'already exists' not in str(e).lower():
                    print(f"[DB] Schema statement skipped: {str(e)[:100]}")
        cur.close()
        self._conn.autocommit = False

    def commit(self):
        try:
            self._conn.commit()
            print("[PG] Commit OK")
        except Exception as e:
            print(f"[PG] Commit error: {e}")

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


class PGCursor:
    def __init__(self, cur, is_insert=False):
        self._cur = cur
        self.lastrowid = None
        self._consumed = False

        if is_insert and cur.description:
            try:
                row = cur.fetchone()
                if row and 'id' in row:
                    self.lastrowid = row['id']
                self._consumed = True
            except Exception:
                pass

    def fetchone(self):
        if self._consumed:
            return None
        try:
            row = self._cur.fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def fetchall(self):
        if self._consumed:
            return []
        try:
            rows = self._cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []


def _convert_sql(sql):
    """Convert SQLite SQL to PostgreSQL."""
    # Parameter placeholders
    sql = sql.replace('?', '%s')

    # Boolean
    sql = sql.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
    sql = sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
    sql = sql.replace('active = 1', 'active = TRUE')
    sql = sql.replace('active = 0', 'active = FALSE')
    sql = sql.replace('agree_terms = 1', 'agree_terms = TRUE')
    sql = sql.replace('used = 0', 'used = FALSE')

    # Date/time functions — SQLite to PostgreSQL
    # Do ALL replacements as complete strings to avoid regex issues
    sql = sql.replace("strftime('%Y-%m', 'now')", "TO_CHAR(NOW(), 'YYYY-MM')")
    sql = sql.replace("strftime('%Y', 'now')", "TO_CHAR(NOW(), 'YYYY')")
    # strftime('%Y-%m', t.created_at) → TO_CHAR(t.created_at, 'YYYY-MM')
    sql = sql.replace("strftime('%Y-%m', t.created_at)", "TO_CHAR(t.created_at, 'YYYY-MM')")
    sql = sql.replace("strftime('%Y', t.created_at)", "TO_CHAR(t.created_at, 'YYYY')")
    sql = sql.replace("strftime('%m', t.created_at)", "TO_CHAR(t.created_at, 'MM')")
    sql = sql.replace("strftime('%Y-%m', p.payment_date)", "TO_CHAR(p.payment_date, 'YYYY-MM')")
    sql = sql.replace("strftime('%Y', p.payment_date)", "TO_CHAR(p.payment_date, 'YYYY')")
    sql = sql.replace("strftime('%Y-%m', last_api_check)", "TO_CHAR(last_api_check, 'YYYY-MM')")
    sql = sql.replace("strftime('%Y-%m', p.created_at)", "TO_CHAR(p.created_at, 'YYYY-MM')")
    sql = sql.replace("strftime('%Y', p.created_at)", "TO_CHAR(p.created_at, 'YYYY')")

    sql = sql.replace("date('now')", "CURRENT_DATE")
    sql = sql.replace("date('now', '+2 days')", "(CURRENT_DATE + INTERVAL '2 days')::date")
    sql = sql.replace("date('now', '-1 day')", "(CURRENT_DATE - INTERVAL '1 day')::date")
    sql = sql.replace("date('now', '-7 days')", "(CURRENT_DATE - INTERVAL '7 days')::date")
    sql = sql.replace("substr(birthday, 6)", "TO_CHAR(birthday, 'MM-DD')")
    # GROUP_CONCAT → STRING_AGG
    sql = sql.replace("GROUP_CONCAT(", "STRING_AGG(")
    # PostgreSQL: DATE fields can't compare with empty string
    sql = sql.replace("birthday != ''", "birthday IS NOT NULL")
    sql = sql.replace("birthday != ''", "birthday IS NOT NULL")

    # INSERT RETURNING for getting lastrowid
    upper = sql.strip().upper()
    if upper.startswith('INSERT') and 'RETURNING' not in upper:
        sql = sql.rstrip().rstrip(';') + ' RETURNING id'

    return sql


def is_postgres():
    return bool(_get_database_url())
