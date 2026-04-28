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
            stripe_customer_id TEXT DEFAULT '',
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
            previous_experience TEXT DEFAULT '',
            member_id       INTEGER,
            follow_up_date  DATE,
            notes           TEXT DEFAULT '',
            archived        BOOLEAN DEFAULT 0,
            archived_at     TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            name            TEXT NOT NULL,
            category        TEXT DEFAULT 'gear',
            sizes           TEXT DEFAULT '',
            colors          TEXT DEFAULT '',
            price           REAL DEFAULT 0,
            stock           INTEGER DEFAULT 0,
            active          BOOLEAN DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            category        TEXT NOT NULL DEFAULT 'other',
            description     TEXT DEFAULT '',
            vendor          TEXT DEFAULT '',
            amount          REAL NOT NULL DEFAULT 0,
            expense_date    DATE DEFAULT CURRENT_DATE,
            recurring        BOOLEAN DEFAULT 0,
            recurring_cycle TEXT DEFAULT 'monthly',
            payment_method  TEXT DEFAULT 'bank_transfer',
            status          TEXT DEFAULT 'paid',
            receipt_url     TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            created_by      INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payroll (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1 REFERENCES academies(id),
            employee_name   TEXT NOT NULL,
            role            TEXT DEFAULT 'instructor',
            salary          REAL DEFAULT 0,
            pay_type        TEXT DEFAULT 'monthly',
            pay_date        DATE DEFAULT CURRENT_DATE,
            hours_worked    REAL DEFAULT 0,
            hourly_rate     REAL DEFAULT 0,
            bonus           REAL DEFAULT 0,
            deductions      REAL DEFAULT 0,
            net_pay         REAL DEFAULT 0,
            status          TEXT DEFAULT 'paid',
            notes           TEXT DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product_variants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            size            TEXT DEFAULT '',
            color           TEXT DEFAULT '',
            stock           INTEGER DEFAULT 0,
            price_override  REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id      INTEGER DEFAULT 1,
            member_id       INTEGER REFERENCES members(id),
            product_id      INTEGER REFERENCES products(id),
            size            TEXT DEFAULT '',
            quantity         INTEGER DEFAULT 1,
            price           REAL DEFAULT 0,
            payment_id      INTEGER REFERENCES payments(id),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        "ALTER TABLE prospects ADD COLUMN previous_experience TEXT DEFAULT ''",
        "ALTER TABLE prospects ADD COLUMN archived BOOLEAN DEFAULT 0",
        "ALTER TABLE prospects ADD COLUMN archived_at TIMESTAMP",
        "ALTER TABLE products ADD COLUMN colors TEXT DEFAULT ''",
        """CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            size TEXT DEFAULT '',
            color TEXT DEFAULT '',
            stock INTEGER DEFAULT 0,
            price_override REAL DEFAULT 0
        )""",
        "ALTER TABLE order_items ADD COLUMN color TEXT DEFAULT ''",
        "ALTER TABLE payment_methods ADD COLUMN stripe_customer_id TEXT DEFAULT ''",
        """CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            experience TEXT DEFAULT '',
            source TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE events ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE events ADD COLUMN landing_color TEXT DEFAULT '#00DC82'",
        "ALTER TABLE events ADD COLUMN landing_headline TEXT DEFAULT ''",
        "ALTER TABLE events ADD COLUMN landing_cta TEXT DEFAULT 'Register Now'",
        "ALTER TABLE events ADD COLUMN landing_bg_style TEXT DEFAULT 'gradient'",
        "ALTER TABLE events ADD COLUMN waiver_text TEXT DEFAULT ''",
        "ALTER TABLE events ADD COLUMN waiver_required BOOLEAN DEFAULT FALSE",
        "ALTER TABLE event_registrations ADD COLUMN waiver_signed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE event_registrations ADD COLUMN waiver_signed_at TIMESTAMP",
        "ALTER TABLE payments ADD COLUMN platform_fee REAL DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN stripe_charge_id TEXT DEFAULT ''",
        """CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS member_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            biometric_enabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_type TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            expo_token TEXT NOT NULL UNIQUE,
            platform TEXT DEFAULT '',
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE academies ADD COLUMN lat REAL DEFAULT 0",
        "ALTER TABLE academies ADD COLUMN lng REAL DEFAULT 0",
        "ALTER TABLE academies ADD COLUMN geofence_radius INTEGER DEFAULT 100",
        """CREATE TABLE IF NOT EXISTS belt_promotion_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            academy_id INTEGER DEFAULT 1,
            current_belt TEXT DEFAULT '',
            current_stripes INTEGER DEFAULT 0,
            requested_belt TEXT DEFAULT '',
            requested_stripes INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            decided_by INTEGER,
            decided_at TIMESTAMP,
            decision_note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            member_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            sender_id INTEGER,
            body TEXT NOT NULL DEFAULT '',
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE programs ADD COLUMN has_belts BOOLEAN DEFAULT FALSE",
        "ALTER TABLE programs ADD COLUMN sport_type TEXT DEFAULT 'other'",
        """CREATE TABLE IF NOT EXISTS programs (
            id SERIAL PRIMARY KEY,
            academy_id INTEGER DEFAULT 1,
            name TEXT NOT NULL DEFAULT '',
            color TEXT DEFAULT '#6366f1',
            description TEXT DEFAULT '',
            active BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE classes ADD COLUMN program_id INTEGER",
        """CREATE TABLE IF NOT EXISTS member_programs (
            id SERIAL PRIMARY KEY,
            member_id INTEGER NOT NULL,
            program_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS calendar_tasks (
            id SERIAL PRIMARY KEY,
            academy_id INTEGER DEFAULT 1,
            user_id INTEGER,
            title TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            task_date DATE NOT NULL,
            task_time TEXT DEFAULT '',
            color TEXT DEFAULT '#6366f1',
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE academies ADD COLUMN media_portal_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE academies ADD COLUMN portal_primary_color TEXT DEFAULT '#6366f1'",
        "ALTER TABLE academies ADD COLUMN portal_welcome TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN portal_price_display TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN portal_token TEXT DEFAULT ''",

        # ─── Unified inbox (multi-channel comms) ───
        # One row per connected channel — Twilio SMS account, Meta page, etc.
        # `config_json` carries channel-specific tokens/IDs. We never read it
        # except inside the channel adapter.
        """CREATE TABLE IF NOT EXISTS inbox_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            kind TEXT NOT NULL,
            name TEXT DEFAULT '',
            config_json TEXT DEFAULT '{}',
            active BOOLEAN DEFAULT TRUE,
            last_synced_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # One thread per (channel, contact). Threads roll up many messages
        # and link back to a member if we matched the contact handle.
        """CREATE TABLE IF NOT EXISTS inbox_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            channel_id INTEGER,
            channel_kind TEXT NOT NULL,
            external_thread_id TEXT DEFAULT '',
            contact_name TEXT DEFAULT '',
            contact_handle TEXT DEFAULT '',
            member_id INTEGER,
            last_message_at TIMESTAMP,
            last_message_preview TEXT DEFAULT '',
            unread_count INTEGER DEFAULT 0,
            archived BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # Direction: 'in' = inbound (member sent us), 'out' = outbound (we sent).
        # `external_id` lets us de-duplicate webhook re-deliveries.
        """CREATE TABLE IF NOT EXISTS inbox_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            direction TEXT NOT NULL,
            body TEXT DEFAULT '',
            attachment_url TEXT DEFAULT '',
            external_id TEXT DEFAULT '',
            sender_label TEXT DEFAULT '',
            ai_drafted BOOLEAN DEFAULT FALSE,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_inbox_threads_academy ON inbox_threads(academy_id, last_message_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_inbox_messages_thread ON inbox_messages(thread_id, sent_at)",

        # ─── Saved message templates for /messaging campaigns ───
        """CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            channel TEXT DEFAULT 'both',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # ─── Automated messages (event-triggered campaigns) ───
        # trigger_type: 'member_created' | 'prospect_created'
        #               | 'member_inactive_15d' | 'payment_failed'
        # delay_minutes: 0 = fire immediately when the event hooks
        #                >0 = fire when scheduler/cron runs after the delay
        """CREATE TABLE IF NOT EXISTS automated_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            trigger_type TEXT NOT NULL,
            name TEXT DEFAULT '',
            channel TEXT DEFAULT 'both',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            delay_minutes INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            last_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # Idempotency log so we don't re-fire the same trigger for the same
        # (member, automation) more than once for the same delay.
        """CREATE TABLE IF NOT EXISTS automated_message_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            automation_id INTEGER NOT NULL,
            recipient_type TEXT NOT NULL,
            recipient_id INTEGER NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_automated_runs_uniq ON automated_message_runs(automation_id, recipient_type, recipient_id)",

        # ─── Message Flows (multi-step drip sequences) ───
        # A flow has N ordered steps. When the flow's trigger fires for a
        # recipient, a flow_execution is created and advances through steps
        # over days as their delays elapse.
        """CREATE TABLE IF NOT EXISTS message_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            audience TEXT DEFAULT 'prospects',
            trigger_type TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS flow_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            delay_days INTEGER DEFAULT 0,
            channel TEXT DEFAULT 'both',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_flow_steps_flow ON flow_steps(flow_id, sequence)",
        """CREATE TABLE IF NOT EXISTS flow_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id INTEGER NOT NULL,
            recipient_type TEXT NOT NULL,
            recipient_id INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_step INTEGER DEFAULT 0,
            last_step_sent_at TIMESTAMP,
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_flow_exec_recipient ON flow_executions(flow_id, recipient_type, recipient_id)",
        "CREATE INDEX IF NOT EXISTS idx_flow_exec_pending ON flow_executions(completed_at, cancelled_at)",

        # ─── Landing pages (lead capture) ───
        # Public-facing pages with lead capture form. Submissions create a
        # prospect, which fires comms automations and flows.
        """CREATE TABLE IF NOT EXISTS landing_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            headline TEXT DEFAULT '',
            body_html TEXT DEFAULT '',
            agreement_text TEXT DEFAULT '',
            header_image_url TEXT DEFAULT '',
            theme_color TEXT DEFAULT '#00DC82',
            cta_label TEXT DEFAULT 'Sign up',
            redirect_url TEXT DEFAULT '',
            ask_phone BOOLEAN DEFAULT TRUE,
            ask_experience BOOLEAN DEFAULT TRUE,
            ask_notes BOOLEAN DEFAULT FALSE,
            signups_count INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS landing_page_signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            prospect_id INTEGER,
            name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            experience TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            agreement_signed BOOLEAN DEFAULT FALSE,
            agreement_signed_at TIMESTAMP,
            user_agent TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_landing_signups_page ON landing_page_signups(page_id, created_at DESC)",

        # ─── Smart Groups (rule-based recipient segmentation) ───
        # rules_json holds an array of predicates ANDed together.
        # Predicate shape: {"field":"belt","op":"eq","value":"Blue"}
        # Fields: belt, status, program_id, last_checkin_days_gt,
        #         last_checkin_days_lt, joined_days_gt, joined_days_lt, gender
        # Ops: eq, neq, gt, lt
        """CREATE TABLE IF NOT EXISTS smart_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            rules_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # ─── Lead capture: ad pixels + waiver ───
        "ALTER TABLE academies ADD COLUMN meta_pixel_id TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN google_ads_id TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN google_ads_label TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN google_analytics_id TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN waiver_required BOOLEAN DEFAULT 0",
        "ALTER TABLE academies ADD COLUMN waiver_text TEXT DEFAULT ''",
        # AI-generated landing page content (JSON blob) and the brief used to create it.
        "ALTER TABLE academies ADD COLUMN landing_content_json TEXT DEFAULT ''",
        "ALTER TABLE academies ADD COLUMN landing_brief TEXT DEFAULT ''",
        # Captured signature for legal record. One row per prospect that signed.
        """CREATE TABLE IF NOT EXISTS lead_waivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academy_id INTEGER DEFAULT 1,
            prospect_id INTEGER NOT NULL,
            signature_name TEXT NOT NULL,
            waiver_text TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_lead_waivers_prospect ON lead_waivers(prospect_id)",
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

    # Backfill trial_start for legacy users
    try:
        conn.execute("UPDATE users SET trial_start = CURRENT_TIMESTAMP WHERE trial_start IS NULL")
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

    # ─── Seed Default Programs ─────────────────────────────────
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM programs").fetchone()
        cnt = row['cnt'] if isinstance(row, dict) else row[0]
        if cnt == 0:
            default_programs = [
                ('Kids Gi', '#f59e0b', 'Gi classes for children (4-15 years)', 1),
                ('Kids No-Gi', '#10b981', 'No-Gi classes for children (4-15 years)', 2),
                ('Adults Gi', '#6366f1', 'Gi classes for adults (16+)', 3),
                ('Adults No-Gi', '#ef4444', 'No-Gi classes for adults (16+)', 4),
                ('Open Mat', '#8b5cf6', 'Free training for all levels', 5),
                ('Competition Team', '#0ea5e9', 'Advanced training for competitors', 6),
            ]
            for name, color, desc, order in default_programs:
                conn.execute(
                    "INSERT INTO programs (academy_id, name, color, description, sort_order) VALUES (1, ?, ?, ?, ?)",
                    (name, color, desc, order)
                )
            conn.commit()
            print("[Seed] Default programs created")
    except Exception as e:
        print(f"[Seed] Programs error: {e}")
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


def list_staff_users_for_academy(academy_id):
    """All active staff/admin users in an academy. Used to fan-out notifications."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, email, phone, role FROM users WHERE academy_id = ? AND active = ?",
        (academy_id, True)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_lead_waiver(academy_id, prospect_id, signature_name, waiver_text='', ip_address='', user_agent=''):
    """Persist a signed waiver row tied to a prospect."""
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO lead_waivers
               (academy_id, prospect_id, signature_name, waiver_text, ip_address, user_agent)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (academy_id, prospect_id, signature_name[:200], (waiver_text or '')[:20000],
             (ip_address or '')[:64], (user_agent or '')[:300])
        )
        conn.commit()
        new_id = cur.lastrowid
    finally:
        conn.close()
    return new_id


def create_user(username, password, name='', email='', phone='', role='user', academy_id=1):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password, name, email, phone, role, academy_id, active, trial_start) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
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


TRIAL_LENGTH_DAYS = 30


def get_trial_days_remaining(user_id):
    """Days remaining in user's trial. Returns 0 if expired or unknown."""
    if not user_id:
        return 0
    from datetime import datetime, timedelta
    conn = get_db()
    try:
        row = conn.execute("SELECT trial_start FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return 0
    row = dict(row) if hasattr(row, 'keys') else row
    ts = row.get('trial_start') if isinstance(row, dict) else None
    if not ts:
        return TRIAL_LENGTH_DAYS  # legacy users without trial_start: treat as fresh
    try:
        if isinstance(ts, str):
            start = datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        else:
            start = ts
        elapsed = (datetime.utcnow() - start).total_seconds()
        remaining = TRIAL_LENGTH_DAYS - int(elapsed // 86400)
        return max(remaining, 0)
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════
#  PASSWORD RESET
# ═══════════════════════════════════════════════════════════════

PASSWORD_RESET_TTL_HOURS = 1


def get_user_by_email(email):
    if not email:
        return None
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND active = ?", (email, True)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def create_password_reset(user_id):
    """Create a one-time reset token. Returns the token string."""
    import secrets
    from datetime import datetime, timedelta
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TTL_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO password_resets (user_id, token, expires_at, used) VALUES (?, ?, ?, ?)",
            (user_id, token, expires_at, False)
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_password_reset(token):
    """Returns the reset record dict if token exists, unused, and not expired. Else None."""
    if not token:
        return None
    from datetime import datetime
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM password_resets WHERE token = ?", (token,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    rec = dict(row)
    if rec.get('used'):
        return None
    exp = rec.get('expires_at')
    try:
        if isinstance(exp, str):
            exp_dt = datetime.strptime(exp[:19], '%Y-%m-%d %H:%M:%S')
        else:
            exp_dt = exp
        if exp_dt and datetime.utcnow() > exp_dt:
            return None
    except Exception:
        return None
    return rec


def consume_password_reset(token, new_password):
    """Validate token, set new password, mark token as used. Returns True on success."""
    rec = get_password_reset(token)
    if not rec:
        return False
    user_id = rec.get('user_id')
    if not user_id:
        return False
    conn = get_db()
    try:
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (_hash_password(new_password), user_id))
        conn.execute("UPDATE password_resets SET used = ? WHERE token = ?", (True, token))
        conn.commit()
    finally:
        conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
#  MEMBER CREDENTIALS (mobile login)
# ═══════════════════════════════════════════════════════════════

def get_member_credential_by_email(email):
    if not email:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM member_credentials WHERE LOWER(email) = LOWER(?)",
            (email,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_member_credential_by_member_id(member_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM member_credentials WHERE member_id = ?",
            (member_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def create_member_credential(member_id, email, password):
    """Create a member credential. Returns the new id, or None on conflict."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO member_credentials (member_id, email, password) VALUES (?, ?, ?)",
            (member_id, email, _hash_password(password))
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[MemberCredentials] Create error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def authenticate_member(email, password):
    """Returns the member dict if credentials valid, else None."""
    cred = get_member_credential_by_email(email)
    if not cred:
        return None
    if not _check_password(password, cred['password']):
        return None
    member = get_member_by_id(cred['member_id'])
    if not member:
        return None
    member = dict(member) if not isinstance(member, dict) else member
    if not member.get('active', True) in (True, 1):
        return None
    # Best-effort touch last_login
    try:
        conn = get_db()
        conn.execute("UPDATE member_credentials SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (cred['id'],))
        conn.commit()
        conn.close()
    except Exception:
        pass
    return member


def set_member_biometric_enabled(member_id, enabled):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE member_credentials SET biometric_enabled = ? WHERE member_id = ?",
            (bool(enabled), member_id)
        )
        conn.commit()
    finally:
        conn.close()


def update_member_credential_password(member_id, new_password):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE member_credentials SET password = ? WHERE member_id = ?",
            (_hash_password(new_password), member_id)
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  DEVICE TOKENS (push notifications)
# ═══════════════════════════════════════════════════════════════

def register_device_token(owner_type, owner_id, expo_token, platform=''):
    """Insert or update a device token. Returns True on success."""
    if owner_type not in ('member', 'staff'):
        return False
    if not expo_token:
        return False
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM device_tokens WHERE expo_token = ?",
            (expo_token,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE device_tokens SET owner_type = ?, owner_id = ?, platform = ?, last_seen = CURRENT_TIMESTAMP WHERE expo_token = ?",
                (owner_type, owner_id, platform, expo_token)
            )
        else:
            conn.execute(
                "INSERT INTO device_tokens (owner_type, owner_id, expo_token, platform) VALUES (?, ?, ?, ?)",
                (owner_type, owner_id, expo_token, platform)
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DeviceTokens] Register error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_device_tokens_for_owner(owner_type, owner_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT expo_token FROM device_tokens WHERE owner_type = ? AND owner_id = ?",
            (owner_type, owner_id)
        ).fetchall()
    finally:
        conn.close()
    return [dict(r)['expo_token'] for r in rows]


def remove_device_token(expo_token):
    conn = get_db()
    try:
        conn.execute("DELETE FROM device_tokens WHERE expo_token = ?", (expo_token,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  BELT PROMOTION REQUESTS (member submits, staff approves)
# ═══════════════════════════════════════════════════════════════

def create_promotion_request(member_id, academy_id, **kwargs):
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO belt_promotion_requests
               (member_id, academy_id, current_belt, current_stripes,
                requested_belt, requested_stripes, message, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (member_id, academy_id,
             kwargs.get('current_belt', ''), kwargs.get('current_stripes', 0),
             kwargs.get('requested_belt', ''), kwargs.get('requested_stripes', 0),
             kwargs.get('message', ''), 'pending')
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[PromotionReq] Create error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def get_promotion_requests_by_member(member_id, limit=20):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM belt_promotion_requests WHERE member_id = ? ORDER BY created_at DESC LIMIT ?",
            (member_id, limit)
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_promotion_requests_for_academy(academy_id, status=None):
    conn = get_db()
    try:
        if status:
            rows = conn.execute(
                """SELECT pr.*, m.first_name, m.last_name, m.email, m.photo
                   FROM belt_promotion_requests pr
                   JOIN members m ON pr.member_id = m.id
                   WHERE pr.academy_id = ? AND pr.status = ?
                   ORDER BY pr.created_at DESC""",
                (academy_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT pr.*, m.first_name, m.last_name, m.email, m.photo
                   FROM belt_promotion_requests pr
                   JOIN members m ON pr.member_id = m.id
                   WHERE pr.academy_id = ?
                   ORDER BY pr.created_at DESC""",
                (academy_id,)
            ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_promotion_request_by_id(req_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM belt_promotion_requests WHERE id = ?",
            (req_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def decide_promotion_request(req_id, decided_by_user_id, status, note=''):
    """status: 'approved' or 'rejected'."""
    if status not in ('approved', 'rejected'):
        return False
    conn = get_db()
    try:
        conn.execute(
            """UPDATE belt_promotion_requests
               SET status = ?, decided_by = ?, decided_at = CURRENT_TIMESTAMP, decision_note = ?
               WHERE id = ?""",
            (status, decided_by_user_id, note, req_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[PromotionReq] Decide error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  CHAT MESSAGES (1:1 between a member and the gym staff)
# ═══════════════════════════════════════════════════════════════

def create_chat_message(academy_id, member_id, sender_type, sender_id, body):
    if sender_type not in ('member', 'staff'):
        return None
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO chat_messages (academy_id, member_id, sender_type, sender_id, body)
               VALUES (?, ?, ?, ?, ?)""",
            (academy_id, member_id, sender_type, sender_id, body)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Chat] Create error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def get_chat_messages(member_id, limit=200):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE member_id = ? ORDER BY created_at ASC LIMIT ?",
            (member_id, limit)
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def mark_chat_read(member_id, by_role):
    """Mark all messages from the OTHER party as read.
    by_role='member' marks staff-sent messages as read; by_role='staff' marks member-sent."""
    other = 'staff' if by_role == 'member' else 'member'
    conn = get_db()
    try:
        conn.execute(
            """UPDATE chat_messages SET read_at = CURRENT_TIMESTAMP
               WHERE member_id = ? AND sender_type = ? AND read_at IS NULL""",
            (member_id, other)
        )
        conn.commit()
    finally:
        conn.close()


def get_chat_threads_for_academy(academy_id, limit=50):
    """Return last message per member-thread within academy."""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT cm.*, m.first_name, m.last_name, m.photo
               FROM chat_messages cm
               JOIN members m ON cm.member_id = m.id
               WHERE cm.academy_id = ? AND cm.id IN (
                   SELECT MAX(id) FROM chat_messages WHERE academy_id = ? GROUP BY member_id
               )
               ORDER BY cm.created_at DESC
               LIMIT ?""",
            (academy_id, academy_id, limit)
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


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
               'phone', 'email', 'website', 'timezone', 'currency', 'language', 'theme',
               'media_portal_enabled', 'portal_primary_color', 'portal_welcome',
               'portal_price_display',
               'meta_pixel_id', 'google_ads_id', 'google_ads_label', 'google_analytics_id',
               'waiver_required', 'waiver_text',
               'landing_content_json', 'landing_brief']
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

    # Fire any 'member_created' automated messages immediately. Wrapped so a
    # broken template never blocks member creation.
    try:
        member = get_member_by_id(new_id)
        if member:
            md = dict(member)
            fire_automation_trigger('member_created', member=md, academy_id=academy_id)
            start_flows_for_trigger('member_created', member=md, academy_id=academy_id)
    except Exception as _e:
        print(f"[create_member] automation hook error: {_e}")

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


def get_attendance_report(academy_id=1, month=None, year=None):
    """Get monthly attendance per member: how many times each trained."""
    from datetime import datetime
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    month_str = f"{year}-{str(month).zfill(2)}"
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT m.id, m.first_name, m.last_name, m.photo,
                   b.name as belt_name, b.color as belt_color,
                   COUNT(ci.id) as total_checkins,
                   MAX(ci.check_in_time) as last_checkin
            FROM members m
            LEFT JOIN check_ins ci ON ci.member_id = m.id
                AND CAST(ci.check_in_time AS TEXT) LIKE ?
            LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
            WHERE m.academy_id = ? AND m.active = 1
            GROUP BY m.id, m.first_name, m.last_name, m.photo, b.name, b.color
            ORDER BY total_checkins DESC
        """, (month_str + '%', academy_id)).fetchall()
    except Exception as e:
        print(f"[Attendance] Error: {e}")
        rows = []
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
    if is_postgres():
        rows = conn.execute(
            """SELECT ci.*, m.first_name, m.last_name, m.photo,
                      b.name as belt_name, b.color as belt_color,
                      c.name as class_name
               FROM check_ins ci
               JOIN members m ON ci.member_id = m.id
               LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
               LEFT JOIN classes c ON ci.class_id = c.id
               WHERE ci.academy_id = ? AND ci.check_in_time::date = CURRENT_DATE
               ORDER BY ci.check_in_time DESC""",
            (academy_id,)
        ).fetchall()
    else:
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
        """SELECT p.*, m.first_name, m.last_name, m.email, m.phone
           FROM payments p
           JOIN members m ON p.member_id = m.id
           WHERE p.id = ?""",
        (payment_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_payments_by_member(member_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM payments WHERE member_id = ? ORDER BY payment_date DESC",
        (member_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_payment(member_id, amount, academy_id=1, **kwargs):
    platform_fee = kwargs.get('platform_fee', 0.30)
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO payments (member_id, academy_id, membership_id, amount, method,
           status, reference, notes, payment_date, due_date, platform_fee, stripe_charge_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (member_id, academy_id, kwargs.get('membership_id'),
         amount, kwargs.get('method', 'cash'),
         kwargs.get('status', 'completed'), kwargs.get('reference', ''),
         kwargs.get('notes', ''), kwargs.get('payment_date', str(date.today())),
         kwargs.get('due_date'), platform_fee, kwargs.get('stripe_charge_id', ''))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    # Fire member_payment_received automations + flows when the payment was
    # actually completed (not just recorded as pending).
    try:
        if (kwargs.get('status', 'completed')) == 'completed':
            member = get_member_by_id(member_id)
            if member:
                md = dict(member)
                md['_payment_amount'] = amount  # available to template authors via {{_payment_amount}} if they want
                fire_automation_trigger('member_payment_received', member=md, academy_id=academy_id)
                start_flows_for_trigger('member_payment_received', member=md, academy_id=academy_id)
    except Exception as _e:
        print(f"[create_payment] automation hook error: {_e}")

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
        """INSERT INTO payment_methods (member_id, method_type, last4, brand, stripe_pm_id, stripe_customer_id, is_default)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (member_id, kwargs.get('method_type', 'credit_card'),
         kwargs.get('last4', ''), kwargs.get('brand', ''),
         kwargs.get('stripe_pm_id', ''), kwargs.get('stripe_customer_id', ''),
         kwargs.get('is_default', False))
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
           source, status, interested_in, previous_experience, member_id, follow_up_date, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (academy_id, kwargs.get('first_name', ''), kwargs.get('last_name', ''),
         kwargs.get('email', ''), kwargs.get('phone', ''),
         kwargs.get('source', ''), kwargs.get('status', 'new'),
         kwargs.get('interested_in', ''), kwargs.get('previous_experience', ''),
         kwargs.get('member_id'),
         kwargs.get('follow_up_date'), kwargs.get('notes', ''))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    # Fire any 'prospect_created' automated messages immediately.
    try:
        prospect_data = {
            'id': new_id,
            'academy_id': academy_id,
            'first_name': kwargs.get('first_name', ''),
            'last_name': kwargs.get('last_name', ''),
            'email': kwargs.get('email', ''),
            'phone': kwargs.get('phone', ''),
        }
        fire_automation_trigger('prospect_created', prospect=prospect_data, academy_id=academy_id)
        start_flows_for_trigger('prospect_created', prospect=prospect_data, academy_id=academy_id)
    except Exception as _e:
        print(f"[create_prospect] automation hook error: {_e}")

    return new_id


def update_prospect(prospect_id, **kwargs):
    conn = get_db()
    allowed = ['first_name', 'last_name', 'email', 'phone', 'source',
               'status', 'follow_up_date', 'notes', 'previous_experience',
               'interested_in', 'archived', 'archived_at']
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
        conn = get_db()
        conn.execute("UPDATE prospects SET status = 'converted', member_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (member_id, prospect_id))
        conn.commit()
        conn.close()
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
    # Ensure new columns exist
    for col, default in [('photo', "''"), ('landing_color', "''"), ('landing_headline', "''"),
                          ('landing_cta', "''"), ('landing_bg_style', "''"),
                          ('waiver_required', 'FALSE'), ('waiver_text', "''")]:
        try:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT DEFAULT {default}")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    try:
        cur = conn.execute(
            """INSERT INTO events (academy_id, name, event_type, description, event_date,
               start_time, end_time, location, max_participants, price, photo, active,
               landing_color, landing_headline, landing_cta, landing_bg_style,
               waiver_required, waiver_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (academy_id, kwargs.get('name', ''), kwargs.get('event_type', 'seminar'),
             kwargs.get('description', ''), kwargs.get('event_date'),
             kwargs.get('start_time', ''), kwargs.get('end_time', ''),
             kwargs.get('location', ''), kwargs.get('max_participants', 0),
             kwargs.get('price', 0), kwargs.get('photo', ''), True,
             kwargs.get('landing_color', '#00DC82'), kwargs.get('landing_headline', ''),
             kwargs.get('landing_cta', 'Register Now'), kwargs.get('landing_bg_style', 'gradient'),
             kwargs.get('waiver_required', False), kwargs.get('waiver_text', ''))
        )
    except Exception:
        # Fallback without new columns
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
               'end_time', 'location', 'max_participants', 'price', 'active', 'photo',
               'landing_color', 'landing_headline', 'landing_cta', 'landing_bg_style',
               'waiver_required', 'waiver_text']
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


def get_member_by_portal_token(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        """SELECT m.*, b.name as belt_name, b.color as belt_color, a.name as academy_name,
                  a.logo as academy_logo, a.portal_primary_color, a.portal_welcome,
                  a.portal_price_display, a.media_portal_enabled
           FROM members m
           LEFT JOIN belt_ranks b ON m.belt_rank_id = b.id
           LEFT JOIN academies a ON m.academy_id = a.id
           WHERE m.portal_token = ?""",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_portal_token(member_id):
    import secrets
    conn = get_db()
    row = conn.execute("SELECT portal_token FROM members WHERE id = ?", (member_id,)).fetchone()
    row_dict = dict(row) if row else {}
    if row_dict.get('portal_token'):
        conn.close()
        return row_dict['portal_token']
    token = secrets.token_urlsafe(16)
    conn.execute("UPDATE members SET portal_token = ? WHERE id = ?", (token, member_id))
    conn.commit()
    conn.close()
    return token


def get_media_for_member(member, academy_id):
    """Return media visible to a member: academy_id match + belt_level = 'all' or member's belt."""
    belt_name = (member.get('belt_name') or '').lower() if member else ''
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM media
           WHERE academy_id = ?
             AND (belt_level = 'all' OR belt_level = '' OR LOWER(belt_level) = ?)
           ORDER BY created_at DESC""",
        (academy_id, belt_name)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


# ─── Message templates ──────────────────────────────────────────

def get_message_templates(academy_id=1):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM message_templates WHERE academy_id = ? ORDER BY name",
            (academy_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_message_template(template_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM message_templates WHERE id = ?",
            (template_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_message_template(academy_id, name, channel='both', subject='', body=''):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO message_templates (academy_id, name, channel, subject, body) VALUES (?,?,?,?,?)",
            (academy_id, name, channel, subject, body)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_message_template(template_id, **kwargs):
    fields, vals = [], []
    for k in ('name', 'channel', 'subject', 'body'):
        if k in kwargs:
            fields.append(f"{k} = ?")
            vals.append(kwargs[k])
    if not fields:
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    vals.append(template_id)
    conn = get_db()
    try:
        conn.execute(
            f"UPDATE message_templates SET {', '.join(fields)} WHERE id = ?",
            vals
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_message_template(template_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM message_templates WHERE id = ?", (template_id,))
        conn.commit()
    finally:
        conn.close()


# ─── Token rendering for messaging ─────────────────────────────
# Substitutes {{first_name}}, {{last_name}}, {{full_name}}, {{email}},
# {{academy_name}}, {{belt}} in subject/body. Missing tokens render as empty
# string so a poorly-tokenized message doesn't ship literal {{x}} to a member.

def render_message_tokens(text, member=None, academy=None):
    if not text:
        return text
    m = member or {}
    a = academy or {}
    if not isinstance(m, dict):
        try:
            m = dict(m)
        except Exception:
            m = {}
    if not isinstance(a, dict):
        try:
            a = dict(a)
        except Exception:
            a = {}
    first = (m.get('first_name') or '').strip()
    last = (m.get('last_name') or '').strip()
    full = (first + ' ' + last).strip()
    repl = {
        '{{first_name}}': first,
        '{{last_name}}': last,
        '{{full_name}}': full,
        '{{name}}': first or full,
        '{{email}}': (m.get('email') or '').strip(),
        '{{phone}}': (m.get('phone') or '').strip(),
        '{{belt}}': (m.get('belt_name') or m.get('belt') or '').strip(),
        '{{academy_name}}': (a.get('name') or '').strip(),
        '{{academy}}': (a.get('name') or '').strip(),
    }
    out = text
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


# ─── Automated messages (event-triggered) ──────────────────────

def get_automated_messages(academy_id=1, trigger_type=None, active_only=False):
    conn = get_db()
    try:
        sql = "SELECT * FROM automated_messages WHERE academy_id = ?"
        params = [academy_id]
        if trigger_type:
            sql += " AND trigger_type = ?"
            params.append(trigger_type)
        if active_only:
            sql += " AND active = ?"
            params.append(True)
        sql += " ORDER BY trigger_type, name"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_automated_message(automation_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM automated_messages WHERE id = ?",
            (automation_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_automated_message(academy_id, trigger_type, **kwargs):
    """Create or update an automation. If automation_id is in kwargs, updates;
    otherwise creates a new row.
    """
    automation_id = kwargs.pop('automation_id', None)
    fields = {
        'name': kwargs.get('name', ''),
        'channel': kwargs.get('channel', 'both'),
        'subject': kwargs.get('subject', ''),
        'body': kwargs.get('body', ''),
        'delay_minutes': int(kwargs.get('delay_minutes', 0) or 0),
        'active': bool(kwargs.get('active', True)),
    }
    conn = get_db()
    try:
        if automation_id:
            conn.execute(
                """UPDATE automated_messages SET
                   trigger_type = ?, name = ?, channel = ?, subject = ?, body = ?,
                   delay_minutes = ?, active = ? WHERE id = ?""",
                (trigger_type, fields['name'], fields['channel'], fields['subject'],
                 fields['body'], fields['delay_minutes'], fields['active'], automation_id)
            )
            conn.commit()
            return automation_id
        cur = conn.execute(
            """INSERT INTO automated_messages
               (academy_id, trigger_type, name, channel, subject, body, delay_minutes, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (academy_id, trigger_type, fields['name'], fields['channel'],
             fields['subject'], fields['body'], fields['delay_minutes'], fields['active'])
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_automated_message(automation_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM automated_messages WHERE id = ?", (automation_id,))
        conn.commit()
    finally:
        conn.close()


def _record_automation_run(automation_id, recipient_type, recipient_id):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO automated_message_runs (automation_id, recipient_type, recipient_id) VALUES (?, ?, ?)",
            (automation_id, recipient_type, recipient_id)
        )
        conn.commit()
    finally:
        conn.close()


def _has_automation_fired(automation_id, recipient_type, recipient_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM automated_message_runs WHERE automation_id = ? AND recipient_type = ? AND recipient_id = ? LIMIT 1",
            (automation_id, recipient_type, recipient_id)
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def fire_automation_trigger(trigger_type, member=None, prospect=None, academy_id=None):
    """Fire all matching automations for a trigger event.

    Looks up active automations for trigger_type, renders tokens, and dispatches
    via notifications_lib (email + sms). Idempotent — won't re-fire the same
    automation for the same recipient.

    Returns count of messages actually sent.
    """
    if academy_id is None:
        if member:
            academy_id = (member.get('academy_id') if isinstance(member, dict) else member['academy_id']) or 1
        elif prospect:
            academy_id = (prospect.get('academy_id') if isinstance(prospect, dict) else prospect['academy_id']) or 1
        else:
            academy_id = 1

    automations = get_automated_messages(academy_id, trigger_type=trigger_type, active_only=True)
    if not automations:
        return 0

    recipient_type = 'member' if member else 'prospect'
    recipient = member or prospect or {}
    if not isinstance(recipient, dict):
        recipient = dict(recipient)
    recipient_id = recipient.get('id')
    if not recipient_id:
        return 0

    try:
        academy = get_academy_by_id(academy_id)
        academy = dict(academy) if academy else {}
    except Exception:
        academy = {}

    sent = 0
    for a in automations:
        # delay_minutes > 0 means "fire later via cron" — skip for immediate hook.
        if int(a.get('delay_minutes') or 0) > 0:
            continue
        if _has_automation_fired(a['id'], recipient_type, recipient_id):
            continue

        subj = render_message_tokens(a.get('subject') or '', recipient, academy)
        body = render_message_tokens(a.get('body') or '', recipient, academy)
        channel = a.get('channel') or 'both'

        try:
            import notifications_lib
            if channel in ('email', 'both') and recipient.get('email'):
                notifications_lib.send_email(recipient['email'], subj or '(no subject)', body)
            if channel in ('sms', 'both') and recipient.get('phone'):
                sms_body = (subj + '\n\n' + body) if subj else body
                notifications_lib.send_sms(recipient['phone'], sms_body[:1500])
        except Exception as e:
            print(f"[Automation {a['id']}] send error: {e}")
            continue

        _record_automation_run(a['id'], recipient_type, recipient_id)
        sent += 1
    return sent


def _send_automation(automation, recipient, academy):
    """Render + dispatch one automation to one recipient. Records the run."""
    subj = render_message_tokens(automation.get('subject') or '', recipient, academy)
    body = render_message_tokens(automation.get('body') or '', recipient, academy)
    channel = automation.get('channel') or 'both'
    try:
        import notifications_lib
        if channel in ('email', 'both') and recipient.get('email'):
            notifications_lib.send_email(recipient['email'], subj or '(no subject)', body)
        if channel in ('sms', 'both') and recipient.get('phone'):
            sms_body = (subj + '\n\n' + body) if subj else body
            notifications_lib.send_sms(recipient['phone'], sms_body[:1500])
    except Exception as e:
        print(f"[Automation {automation.get('id')}] send error: {e}")
        return False
    _record_automation_run(automation['id'], 'member', recipient['id'])
    return True


def run_due_delayed_automations(academy_id=1):
    """Run automations that need to fire on a schedule.

    Handles:
    - member_inactive_15d: members with no check-in in 15+ days
    - member_birthday: members whose date_of_birth (MM-DD) matches today
    - member_membership_expiring_7d: memberships with end_date == today + 7
    - payment_failed: skipped — fired directly from Stripe webhook in
      production when wired

    Designed to be called from a Railway cron job hitting the authenticated
    endpoint /automations/run-now, OR from a "Run now" button in the UI.
    """
    from datetime import date as _date, timedelta as _td, datetime as _dt
    fired = 0
    automations = get_automated_messages(academy_id, active_only=True)
    if not automations:
        return 0

    academy = get_academy_by_id(academy_id)
    academy = dict(academy) if academy else {}

    today = _date.today()
    today_mmdd = today.strftime('%m-%d')

    by_trigger = {}
    for a in automations:
        by_trigger.setdefault(a['trigger_type'], []).append(a)

    try:
        members = get_all_members(academy_id) or []
    except Exception:
        members = []

    # ── member_inactive_15d ──
    for a in by_trigger.get('member_inactive_15d', []):
        for m in members:
            md = m if isinstance(m, dict) else dict(m)
            if not md.get('active'):
                continue
            if _has_automation_fired(a['id'], 'member', md['id']):
                continue
            try:
                checkins = get_checkins_by_member(md['id'], limit=1) or []
            except Exception:
                checkins = []
            if checkins:
                last_at = str(checkins[0].get('created_at', ''))[:10]
                try:
                    last_dt = _dt.strptime(last_at, '%Y-%m-%d').date()
                    days_since = (today - last_dt).days
                    if days_since < 15:
                        continue
                except Exception:
                    continue
            if _send_automation(a, md, academy):
                fired += 1

    # ── member_birthday ── fires once per year per (automation, member) since
    # the idempotency key includes year via record_automation_run timestamp;
    # _has_automation_fired returns true if EVER fired, so we'd only fire
    # once total — instead we annotate the run with year by passing a
    # year-suffixed automation_id virtual key.
    for a in by_trigger.get('member_birthday', []):
        for m in members:
            md = m if isinstance(m, dict) else dict(m)
            dob = str(md.get('date_of_birth') or '')[:10]
            if not dob or len(dob) < 5:
                continue
            mmdd = dob[5:10] if len(dob) >= 10 else dob[-5:]
            if mmdd != today_mmdd:
                continue
            # Year-scoped idempotency: encode year into the recipient_id key
            # so next year's birthday fires again. We hash member_id with year.
            virtual_recipient = int(f"{today.year}{md['id']:07d}")
            if _has_automation_fired(a['id'], 'member_yearly', virtual_recipient):
                continue
            if _send_automation(a, md, academy):
                _record_automation_run(a['id'], 'member_yearly', virtual_recipient)
                fired += 1

    # ── member_membership_expiring_7d ──
    target_date = today + _td(days=7)
    target_str = target_date.strftime('%Y-%m-%d')
    for a in by_trigger.get('member_membership_expiring_7d', []):
        for m in members:
            md = m if isinstance(m, dict) else dict(m)
            if not md.get('active'):
                continue
            try:
                memberships = get_memberships_by_member(md['id']) or []
            except Exception:
                memberships = []
            matched = False
            for ms in memberships:
                msd = ms if isinstance(ms, dict) else dict(ms)
                if (msd.get('status') == 'active'
                    and str(msd.get('end_date') or '')[:10] == target_str):
                    matched = True; break
            if not matched:
                continue
            if _has_automation_fired(a['id'], 'member', md['id']):
                continue
            if _send_automation(a, md, academy):
                fired += 1

    return fired


# ─── Message Flows (multi-step drip sequences) ─────────────────

def get_flows(academy_id=1, active_only=False):
    conn = get_db()
    try:
        sql = "SELECT * FROM message_flows WHERE academy_id = ?"
        params = [academy_id]
        if active_only:
            sql += " AND active = ?"
            params.append(True)
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # AS-alias the count and read by name so this works under both
            # sqlite3 (Row supports [0]) AND psycopg2 RealDictCursor (dict).
            count_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM flow_steps WHERE flow_id = ?", (d['id'],)
            ).fetchone()
            if count_row is None:
                d['step_count'] = 0
            elif isinstance(count_row, dict):
                d['step_count'] = count_row.get('cnt') or 0
            else:
                d['step_count'] = count_row[0] or 0
            out.append(d)
        return out
    finally:
        conn.close()


def get_flow(flow_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM message_flows WHERE id = ?", (flow_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_flow_steps(flow_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM flow_steps WHERE flow_id = ? ORDER BY sequence ASC",
            (flow_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_flow(academy_id, **kwargs):
    """Create or update a flow. Returns flow_id."""
    flow_id = kwargs.get('flow_id')
    payload = (
        kwargs.get('name', ''),
        kwargs.get('audience', 'prospects'),
        kwargs.get('trigger_type', 'prospect_created'),
        bool(kwargs.get('active', True)),
    )
    conn = get_db()
    try:
        if flow_id:
            conn.execute(
                "UPDATE message_flows SET name=?, audience=?, trigger_type=?, active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                payload + (flow_id,)
            )
            conn.commit()
            return flow_id
        cur = conn.execute(
            "INSERT INTO message_flows (academy_id, name, audience, trigger_type, active) VALUES (?, ?, ?, ?, ?)",
            (academy_id,) + payload
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_flow(flow_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM flow_steps WHERE flow_id = ?", (flow_id,))
        conn.execute("DELETE FROM flow_executions WHERE flow_id = ?", (flow_id,))
        conn.execute("DELETE FROM message_flows WHERE id = ?", (flow_id,))
        conn.commit()
    finally:
        conn.close()


def set_flow_steps(flow_id, steps):
    """Replace all steps for a flow with the provided list.

    steps: list of dicts {sequence, delay_days, channel, subject, body}.
    Sequence is 0-indexed.
    """
    conn = get_db()
    try:
        conn.execute("DELETE FROM flow_steps WHERE flow_id = ?", (flow_id,))
        for i, s in enumerate(steps):
            conn.execute(
                "INSERT INTO flow_steps (flow_id, sequence, delay_days, channel, subject, body) VALUES (?, ?, ?, ?, ?, ?)",
                (flow_id, i,
                 int(s.get('delay_days', 0) or 0),
                 s.get('channel', 'both'),
                 s.get('subject', ''),
                 s.get('body', ''))
            )
        conn.execute("UPDATE message_flows SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (flow_id,))
        conn.commit()
    finally:
        conn.close()


def start_flow_execution(flow_id, recipient_type, recipient_id):
    """Begin a flow for a recipient. Idempotent — won't double-start an active
    execution for the same (flow, recipient).
    """
    conn = get_db()
    try:
        existing = conn.execute(
            """SELECT id FROM flow_executions
               WHERE flow_id = ? AND recipient_type = ? AND recipient_id = ?
               AND completed_at IS NULL AND cancelled_at IS NULL""",
            (flow_id, recipient_type, recipient_id)
        ).fetchone()
        if existing:
            return None
        cur = conn.execute(
            """INSERT INTO flow_executions
               (flow_id, recipient_type, recipient_id, started_at, current_step)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP, 0)""",
            (flow_id, recipient_type, recipient_id)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def start_flows_for_trigger(trigger_type, member=None, prospect=None, academy_id=None):
    """Start every active flow whose trigger matches this event."""
    if academy_id is None:
        if member:
            academy_id = (member.get('academy_id') if isinstance(member, dict) else member['academy_id']) or 1
        elif prospect:
            academy_id = (prospect.get('academy_id') if isinstance(prospect, dict) else prospect['academy_id']) or 1
        else:
            academy_id = 1

    flows = get_flows(academy_id, active_only=True)
    flows = [f for f in flows if f.get('trigger_type') == trigger_type and f.get('step_count', 0) > 0]
    if not flows:
        return 0

    recipient_type = 'member' if member else 'prospect'
    recipient = member or prospect or {}
    if not isinstance(recipient, dict):
        recipient = dict(recipient)
    recipient_id = recipient.get('id')
    if not recipient_id:
        return 0

    started = 0
    for f in flows:
        if start_flow_execution(f['id'], recipient_type, recipient_id):
            started += 1
    return started


def advance_flow_executions(academy_id=1):
    """Advance every active flow execution whose next step's delay has elapsed.

    Returns count of step messages actually sent.

    Logic:
    - For each pending execution (no completed_at, no cancelled_at):
      - Look up the step at current_step
      - If no such step → mark completed
      - Compute "ready time" = started_at + sum(delay_days[0..current_step])
      - If now >= ready_time AND (last_step_sent_at is None OR step delay
        elapsed since it): send the message and advance
    """
    from datetime import datetime as _dt, timedelta as _td

    flows = {f['id']: f for f in get_flows(academy_id)}
    if not flows:
        return 0

    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM flow_executions
               WHERE completed_at IS NULL AND cancelled_at IS NULL"""
        ).fetchall()
        executions = [dict(r) for r in rows]
    finally:
        conn.close()

    if not executions:
        return 0

    sent = 0
    for ex in executions:
        flow = flows.get(ex['flow_id'])
        if not flow:
            continue
        steps = get_flow_steps(ex['flow_id'])
        cur_idx = ex.get('current_step', 0) or 0
        if cur_idx >= len(steps):
            _mark_flow_completed(ex['id'])
            continue
        step = steps[cur_idx]

        # Time when this step is due. Anchor: previous step's send time, or
        # started_at if cur_idx == 0.
        try:
            anchor_str = ex.get('last_step_sent_at') or ex.get('started_at')
            anchor_str = str(anchor_str)[:19].replace('T', ' ')
            anchor = _dt.strptime(anchor_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            anchor = _dt.utcnow()

        due_at = anchor + _td(days=int(step.get('delay_days', 0) or 0))
        if _dt.utcnow() < due_at:
            continue

        # Resolve recipient
        recipient = None
        try:
            if ex['recipient_type'] == 'member':
                m = get_member_by_id(ex['recipient_id'])
                recipient = dict(m) if m else None
            elif ex['recipient_type'] == 'prospect':
                p = get_prospect_by_id(ex['recipient_id'])
                recipient = dict(p) if p else None
        except Exception:
            recipient = None
        if not recipient:
            _mark_flow_cancelled(ex['id'])
            continue

        try:
            academy = get_academy_by_id(recipient.get('academy_id', academy_id))
            academy = dict(academy) if academy else {}
        except Exception:
            academy = {}

        subject = render_message_tokens(step.get('subject', '') or '', recipient, academy)
        body = render_message_tokens(step.get('body', '') or '', recipient, academy)
        channel = step.get('channel', 'both')

        try:
            import notifications_lib
            if channel in ('email', 'both') and recipient.get('email'):
                notifications_lib.send_email(recipient['email'], subject or '(no subject)', body)
            if channel in ('sms', 'both') and recipient.get('phone'):
                sms_body = (subject + '\n\n' + body) if subject else body
                notifications_lib.send_sms(recipient['phone'], sms_body[:1500])
        except Exception as e:
            print(f"[Flow {flow['id']} step {cur_idx}] send error: {e}")
            continue

        _advance_flow_execution(ex['id'], cur_idx + 1, complete=(cur_idx + 1 >= len(steps)))
        sent += 1
    return sent


def _advance_flow_execution(execution_id, new_step, complete=False):
    conn = get_db()
    try:
        if complete:
            conn.execute(
                "UPDATE flow_executions SET current_step = ?, last_step_sent_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_step, execution_id)
            )
        else:
            conn.execute(
                "UPDATE flow_executions SET current_step = ?, last_step_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_step, execution_id)
            )
        conn.commit()
    finally:
        conn.close()


def _mark_flow_completed(execution_id):
    conn = get_db()
    try:
        conn.execute("UPDATE flow_executions SET completed_at = CURRENT_TIMESTAMP WHERE id = ?", (execution_id,))
        conn.commit()
    finally:
        conn.close()


def _mark_flow_cancelled(execution_id):
    conn = get_db()
    try:
        conn.execute("UPDATE flow_executions SET cancelled_at = CURRENT_TIMESTAMP WHERE id = ?", (execution_id,))
        conn.commit()
    finally:
        conn.close()


# ─── Landing pages (lead capture) ─────────────────────────────

import re as _re_landing


def _slugify(text):
    s = (text or '').lower().strip()
    s = _re_landing.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s or 'landing'


def get_landing_pages(academy_id=1):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM landing_pages WHERE academy_id = ? ORDER BY updated_at DESC",
            (academy_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_landing_page(page_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM landing_pages WHERE id = ?", (page_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_landing_page_by_slug(slug):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM landing_pages WHERE slug = ? AND active = ?",
            (slug, True)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_landing_page(academy_id, **kwargs):
    """Insert or update a landing page. Slug auto-generates from title if blank."""
    page_id = kwargs.get('page_id')
    title = (kwargs.get('title') or '').strip() or 'Untitled'
    slug = (kwargs.get('slug') or '').strip()
    if not slug:
        slug = _slugify(title)
    # Avoid slug collision by appending the page_id or a counter when needed.
    conn = get_db()
    try:
        if not page_id:
            base = slug
            counter = 2
            while conn.execute(
                "SELECT 1 FROM landing_pages WHERE slug = ?", (slug,)
            ).fetchone():
                slug = f"{base}-{counter}"
                counter += 1

        payload = (
            slug, title,
            kwargs.get('headline', ''),
            kwargs.get('body_html', ''),
            kwargs.get('agreement_text', ''),
            kwargs.get('header_image_url', ''),
            kwargs.get('theme_color', '#00DC82'),
            kwargs.get('cta_label', 'Sign up'),
            kwargs.get('redirect_url', ''),
            bool(kwargs.get('ask_phone', True)),
            bool(kwargs.get('ask_experience', True)),
            bool(kwargs.get('ask_notes', False)),
            bool(kwargs.get('active', True)),
        )

        if page_id:
            conn.execute(
                """UPDATE landing_pages SET
                   slug=?, title=?, headline=?, body_html=?, agreement_text=?,
                   header_image_url=?, theme_color=?, cta_label=?, redirect_url=?,
                   ask_phone=?, ask_experience=?, ask_notes=?, active=?,
                   updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                payload + (page_id,)
            )
            conn.commit()
            return page_id
        cur = conn.execute(
            """INSERT INTO landing_pages
               (academy_id, slug, title, headline, body_html, agreement_text,
                header_image_url, theme_color, cta_label, redirect_url,
                ask_phone, ask_experience, ask_notes, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (academy_id,) + payload
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_landing_page(page_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM landing_page_signups WHERE page_id = ?", (page_id,))
        conn.execute("DELETE FROM landing_pages WHERE id = ?", (page_id,))
        conn.commit()
    finally:
        conn.close()


def record_landing_signup(page_id, **kwargs):
    """Persist a landing page form submission and bump signups_count."""
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO landing_page_signups
               (page_id, prospect_id, name, email, phone, experience, notes,
                agreement_signed, agreement_signed_at, user_agent, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (page_id,
             kwargs.get('prospect_id'),
             kwargs.get('name', ''),
             kwargs.get('email', ''),
             kwargs.get('phone', ''),
             kwargs.get('experience', ''),
             kwargs.get('notes', ''),
             bool(kwargs.get('agreement_signed', False)),
             kwargs.get('agreement_signed_at'),
             kwargs.get('user_agent', '')[:500],
             kwargs.get('ip_address', '')[:64])
        )
        conn.execute(
            "UPDATE landing_pages SET signups_count = signups_count + 1 WHERE id = ?",
            (page_id,)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_landing_signups(page_id, limit=200):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM landing_page_signups WHERE page_id = ? ORDER BY created_at DESC LIMIT ?",
            (page_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Smart Groups (rule-based segmentation) ────────────────────

def get_smart_groups(academy_id=1):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM smart_groups WHERE academy_id = ? ORDER BY name",
            (academy_id,)
        ).fetchall()
        out = []
        import json as _json
        for r in rows:
            d = dict(r)
            try:
                d['rules'] = _json.loads(d.get('rules_json') or '[]')
            except Exception:
                d['rules'] = []
            out.append(d)
        return out
    finally:
        conn.close()


def get_smart_group(group_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM smart_groups WHERE id = ?", (group_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        import json as _json
        try:
            d['rules'] = _json.loads(d.get('rules_json') or '[]')
        except Exception:
            d['rules'] = []
        return d
    finally:
        conn.close()


def upsert_smart_group(academy_id, **kwargs):
    import json as _json
    group_id = kwargs.get('group_id')
    name = kwargs.get('name', '').strip()
    description = kwargs.get('description', '').strip()
    rules = kwargs.get('rules') or []
    rules_json = _json.dumps(rules)
    conn = get_db()
    try:
        if group_id:
            conn.execute(
                "UPDATE smart_groups SET name=?, description=?, rules_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (name, description, rules_json, group_id)
            )
            conn.commit()
            return group_id
        cur = conn.execute(
            "INSERT INTO smart_groups (academy_id, name, description, rules_json) VALUES (?, ?, ?, ?)",
            (academy_id, name, description, rules_json)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_smart_group(group_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM smart_groups WHERE id = ?", (group_id,))
        conn.commit()
    finally:
        conn.close()


def evaluate_smart_group(group_id, academy_id=1):
    """Return the list of member dicts that match all predicates in this group.

    Predicates are AND'd. Each predicate has {field, op, value}. The empty
    rules list matches everyone (acts like "all members").
    """
    group = get_smart_group(group_id)
    if not group:
        return []
    rules = group.get('rules') or []
    return _evaluate_member_rules(rules, academy_id)


def _evaluate_member_rules(rules, academy_id=1):
    """Return members matching every rule. Reused by smart-group preview."""
    from datetime import date as _date, datetime as _dt

    members = get_all_members(academy_id) or []
    if not rules:
        return [dict(m) for m in members]

    today = _date.today()
    out = []
    for m in members:
        md = m if isinstance(m, dict) else dict(m)
        keep = True
        last_checkin_days = None
        for rule in rules:
            field = rule.get('field')
            op = rule.get('op', 'eq')
            value = rule.get('value', '')

            if field == 'belt':
                got = (md.get('belt_name') or md.get('belt') or '').lower()
                want = (value or '').lower()
                if op == 'eq' and got != want: keep = False; break
                if op == 'neq' and got == want: keep = False; break

            elif field == 'status':
                got = (md.get('membership_status') or '').lower()
                want = (value or '').lower()
                if op == 'eq' and got != want: keep = False; break
                if op == 'neq' and got == want: keep = False; break

            elif field == 'gender':
                got = (md.get('gender') or '').lower()
                want = (value or '').lower()
                if op == 'eq' and got != want: keep = False; break
                if op == 'neq' and got == want: keep = False; break

            elif field == 'program_id':
                try:
                    progs = get_member_programs(md['id']) or []
                    program_ids = [p.get('program_id') for p in progs]
                    want_id = int(value)
                    if op == 'eq' and want_id not in program_ids: keep = False; break
                    if op == 'neq' and want_id in program_ids: keep = False; break
                except Exception:
                    keep = False; break

            elif field == 'last_checkin_days_gt' or field == 'last_checkin_days_lt':
                if last_checkin_days is None:
                    try:
                        cks = get_checkins_by_member(md['id'], limit=1) or []
                    except Exception:
                        cks = []
                    if cks:
                        last_at = str(cks[0].get('created_at', ''))[:10]
                        try:
                            last_dt = _dt.strptime(last_at, '%Y-%m-%d').date()
                            last_checkin_days = (today - last_dt).days
                        except Exception:
                            last_checkin_days = 99999  # never checked in
                    else:
                        last_checkin_days = 99999
                try:
                    threshold = int(value)
                except Exception:
                    threshold = 0
                if field == 'last_checkin_days_gt' and not (last_checkin_days > threshold):
                    keep = False; break
                if field == 'last_checkin_days_lt' and not (last_checkin_days < threshold):
                    keep = False; break

            elif field == 'joined_days_gt' or field == 'joined_days_lt':
                join_str = str(md.get('join_date', ''))[:10]
                try:
                    join_dt = _dt.strptime(join_str, '%Y-%m-%d').date()
                    joined_days = (today - join_dt).days
                except Exception:
                    keep = False; break
                try:
                    threshold = int(value)
                except Exception:
                    threshold = 0
                if field == 'joined_days_gt' and not (joined_days > threshold):
                    keep = False; break
                if field == 'joined_days_lt' and not (joined_days < threshold):
                    keep = False; break

        if keep:
            out.append(md)
    return out


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
    elif filter_type == 'program':
        # Members enrolled in a specific program
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               JOIN member_programs mp ON mp.member_id = m.id
               WHERE m.academy_id = ? AND mp.program_id = ? AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id, int(filter_value))
        ).fetchall()
    elif filter_type == 'former':
        # Ex-alunos (inactive members)
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               WHERE m.academy_id = ? AND m.active = 0
               ORDER BY m.last_name, m.first_name""",
            (academy_id,)
        ).fetchall()
    elif filter_type == 'leads':
        # Prospects/Leads
        rows = conn.execute(
            """SELECT p.id, p.first_name, p.last_name, p.email, p.phone
               FROM prospects p
               WHERE p.academy_id = ? AND (p.status IS NULL OR p.status != 'converted')
               ORDER BY p.last_name, p.first_name""",
            (academy_id,)
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
    # Fix NULLs first in separate connection
    try:
        c = get_db()
        c.execute("UPDATE members SET membership_status = 'active' WHERE membership_status IS NULL OR membership_status = ''")
        c.execute("UPDATE members SET academy_id = 1 WHERE academy_id IS NULL")
        c.commit()
        c.close()
    except Exception as e:
        print(f"[Stats] Fix NULLs error: {e}")

    conn = get_db()
    stats = {}

    # Active members — simple count, no filters that could fail
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM members WHERE academy_id = ? AND membership_status = 'active'",
            (academy_id,)
        ).fetchone()
        stats['active_members'] = row['cnt'] if isinstance(row, dict) else row[0]
        print(f"[Stats] Active members for academy {academy_id}: {stats['active_members']}")
    except Exception as e:
        print(f"[Stats] Active members error: {e}")
        # Fallback — count ALL members
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM members WHERE academy_id = ?", (academy_id,)).fetchone()
            stats['active_members'] = row['cnt'] if isinstance(row, dict) else row[0]
        except Exception:
            stats['active_members'] = 0

    # Total members
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM members WHERE academy_id = ?", (academy_id,)).fetchone()
        stats['total_members'] = row['cnt'] if isinstance(row, dict) else row[0]
    except Exception:
        stats['total_members'] = 0

    # Today check-ins
    try:
        if is_postgres():
            row = conn.execute("SELECT COUNT(*) as cnt FROM check_ins WHERE academy_id = ? AND check_in_time::date = CURRENT_DATE", (academy_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM check_ins WHERE academy_id = ? AND DATE(check_in_time) = date('now')", (academy_id,)).fetchone()
        stats['today_checkins'] = row['cnt'] if isinstance(row, dict) else row[0]
    except Exception:
        stats['today_checkins'] = 0

    # Monthly revenue
    try:
        if is_postgres():
            row = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE academy_id = ? AND status = 'completed' AND to_char(payment_date::date, 'YYYY-MM') = to_char(CURRENT_DATE, 'YYYY-MM')", (academy_id,)).fetchone()
        else:
            row = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE academy_id = ? AND status = 'completed' AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')", (academy_id,)).fetchone()
        stats['monthly_revenue'] = row['total'] if isinstance(row, dict) else row[0]
    except Exception:
        stats['monthly_revenue'] = 0

    # Expiring memberships
    try:
        if is_postgres():
            row = conn.execute("SELECT COUNT(*) as cnt FROM memberships ms JOIN members m ON ms.member_id = m.id WHERE m.academy_id = ? AND ms.status = 'active' AND ms.end_date IS NOT NULL AND ms.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'", (academy_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM memberships ms JOIN members m ON ms.member_id = m.id WHERE m.academy_id = ? AND ms.status = 'active' AND ms.end_date IS NOT NULL AND ms.end_date BETWEEN date('now') AND date('now', '+30 days')", (academy_id,)).fetchone()
        stats['expiring_soon'] = row['cnt'] if isinstance(row, dict) else row[0]
    except Exception:
        stats['expiring_soon'] = 0

    # Prospects count
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM prospects WHERE academy_id = ? AND status NOT IN ('converted', 'lost')", (academy_id,)).fetchone()
        stats['active_prospects'] = row['cnt'] if isinstance(row, dict) else row[0]
    except Exception:
        stats['active_prospects'] = 0

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


# ═══════════════════════════════════════════════════════════════
# Calendar Tasks
# ═══════════════════════════════════════════════════════════════

def get_calendar_tasks(academy_id=1, month=None, year=None):
    from datetime import datetime
    if not month: month = datetime.now().month
    if not year: year = datetime.now().year
    month_str = f"{year}-{str(month).zfill(2)}"
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM calendar_tasks WHERE academy_id = ? AND CAST(task_date AS TEXT) LIKE ? ORDER BY task_date, task_time",
            (academy_id, month_str + '%')
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def get_today_tasks(academy_id=1):
    from datetime import date
    today = date.today().isoformat()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM calendar_tasks WHERE academy_id = ? AND CAST(task_date AS TEXT) = ? AND completed = FALSE ORDER BY task_time",
            (academy_id, today)
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def add_calendar_task(academy_id, user_id, title, task_date, description='', task_time='', color='#6366f1'):
    conn = get_db()
    conn.execute(
        "INSERT INTO calendar_tasks (academy_id, user_id, title, task_date, description, task_time, color) VALUES (?,?,?,?,?,?,?)",
        (academy_id, user_id, title, task_date, description, task_time, color)
    )
    conn.commit()
    conn.close()


def update_calendar_task(task_id, **kwargs):
    conn = get_db()
    for k, v in kwargs.items():
        try:
            conn.execute(f"UPDATE calendar_tasks SET {k} = ? WHERE id = ?", (v, task_id))
        except Exception:
            pass
    conn.commit()
    conn.close()


def delete_calendar_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM calendar_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# Programs
# ═══════════════════════════════════════════════════════════════

def get_programs(academy_id=1):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM programs WHERE academy_id = ? ORDER BY sort_order, name", (academy_id,)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def get_program(program_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM programs WHERE id = ?", (program_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_program(academy_id, name, color='#6366f1', description=''):
    conn = get_db()
    conn.execute("INSERT INTO programs (academy_id, name, color, description) VALUES (?,?,?,?)",
                 (academy_id, name, color, description))
    conn.commit()
    conn.close()


def update_program(program_id, **kwargs):
    conn = get_db()
    for k, v in kwargs.items():
        try:
            conn.execute(f"UPDATE programs SET {k} = ? WHERE id = ?", (v, program_id))
        except Exception:
            pass
    conn.commit()
    conn.close()


def delete_program(program_id):
    conn = get_db()
    conn.execute("DELETE FROM programs WHERE id = ?", (program_id,))
    conn.commit()
    conn.close()


def enroll_member_program(member_id, program_id):
    conn = get_db()
    try:
        conn.execute("INSERT INTO member_programs (member_id, program_id) VALUES (?,?)", (member_id, program_id))
        conn.commit()
    except Exception:
        pass
    conn.close()


def unenroll_member_program(member_id, program_id):
    conn = get_db()
    conn.execute("DELETE FROM member_programs WHERE member_id = ? AND program_id = ?", (member_id, program_id))
    conn.commit()
    conn.close()


def get_member_programs(member_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT p.* FROM programs p JOIN member_programs mp ON mp.program_id = p.id WHERE mp.member_id = ? ORDER BY p.name",
            (member_id,)
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def get_members_by_program(academy_id, program_id):
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT m.id, m.first_name, m.last_name, m.email, m.phone
               FROM members m
               JOIN member_programs mp ON mp.member_id = m.id
               WHERE m.academy_id = ? AND mp.program_id = ? AND m.active = 1
               ORDER BY m.last_name, m.first_name""",
            (academy_id, program_id)
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# Products / Store
# ═══════════════════════════════════════════════════════════════

def get_all_products(academy_id=1):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM products WHERE academy_id = ? AND active = 1 ORDER BY name", (academy_id,)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def create_product(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (academy_id, name, category, sizes, colors, price, stock) VALUES (?,?,?,?,?,?,?)",
        (academy_id, kwargs.get('name', ''), kwargs.get('category', 'gear'),
         kwargs.get('sizes', ''), kwargs.get('colors', ''), kwargs.get('price', 0), kwargs.get('stock', 0))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_product(product_id, **kwargs):
    conn = get_db()
    allowed = ['name', 'category', 'sizes', 'colors', 'price', 'stock', 'active']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(product_id)
    conn.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return True


def get_product_variants(product_id):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY color, size", (product_id,)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def set_product_variants(product_id, variants):
    """Replace all variants for a product. variants = [{size, color, stock, price_override}]"""
    conn = get_db()
    conn.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
    for v in variants:
        conn.execute(
            "INSERT INTO product_variants (product_id, size, color, stock, price_override) VALUES (?,?,?,?,?)",
            (product_id, v.get('size', ''), v.get('color', ''), int(v.get('stock', 0)), float(v.get('price_override', 0)))
        )
    # Update total stock on product
    total = sum(int(v.get('stock', 0)) for v in variants)
    conn.execute("UPDATE products SET stock = ? WHERE id = ?", (total, product_id))
    conn.commit()
    conn.close()


def create_order_item(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO order_items (academy_id, member_id, product_id, size, color, quantity, price, payment_id) VALUES (?,?,?,?,?,?,?,?)",
        (academy_id, kwargs.get('member_id'), kwargs.get('product_id'),
         kwargs.get('size', ''), kwargs.get('color', ''), kwargs.get('quantity', 1),
         kwargs.get('price', 0), kwargs.get('payment_id'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ═══════════════════════════════════════════════════════════════
# EXPENSES
# ═══════════════════════════════════════════════════════════════

def get_all_expenses(academy_id=1, month=None, year=None):
    conn = get_db()
    try:
        if month and year:
            month_str = f"{year}-{str(month).zfill(2)}"
            rows = conn.execute(
                "SELECT * FROM expenses WHERE academy_id = ? AND CAST(expense_date AS TEXT) LIKE ? ORDER BY expense_date DESC",
                (academy_id, month_str + '%')
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE academy_id = ? ORDER BY expense_date DESC",
                (academy_id,)
            ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def create_expense(academy_id=1, **kwargs):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO expenses (academy_id, category, description, vendor, amount,
           expense_date, recurring, recurring_cycle, payment_method, status, notes, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (academy_id, kwargs.get('category', 'other'), kwargs.get('description', ''),
         kwargs.get('vendor', ''), float(kwargs.get('amount', 0)),
         kwargs.get('expense_date', str(date.today())),
         kwargs.get('recurring', False), kwargs.get('recurring_cycle', 'monthly'),
         kwargs.get('payment_method', 'bank_transfer'), kwargs.get('status', 'paid'),
         kwargs.get('notes', ''), kwargs.get('created_by'))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_expense(expense_id, **kwargs):
    conn = get_db()
    allowed = ['category', 'description', 'vendor', 'amount', 'expense_date',
               'recurring', 'recurring_cycle', 'payment_method', 'status', 'notes']
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(expense_id)
    conn.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return True


def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════════════
# PAYROLL
# ═══════════════════════════════════════════════════════════════

def get_all_payroll(academy_id=1, month=None, year=None):
    conn = get_db()
    try:
        if month and year:
            month_str = f"{year}-{str(month).zfill(2)}"
            rows = conn.execute(
                "SELECT * FROM payroll WHERE academy_id = ? AND CAST(pay_date AS TEXT) LIKE ? ORDER BY pay_date DESC",
                (academy_id, month_str + '%')
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payroll WHERE academy_id = ? ORDER BY pay_date DESC", (academy_id,)
            ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


def create_payroll(academy_id=1, **kwargs):
    salary = float(kwargs.get('salary', 0))
    bonus = float(kwargs.get('bonus', 0))
    deductions = float(kwargs.get('deductions', 0))
    hours = float(kwargs.get('hours_worked', 0))
    rate = float(kwargs.get('hourly_rate', 0))
    if kwargs.get('pay_type') == 'hourly' and hours and rate:
        net = (hours * rate) + bonus - deductions
    else:
        net = salary + bonus - deductions
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO payroll (academy_id, employee_name, role, salary, pay_type,
           pay_date, hours_worked, hourly_rate, bonus, deductions, net_pay, status, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (academy_id, kwargs.get('employee_name', ''), kwargs.get('role', 'instructor'),
         salary, kwargs.get('pay_type', 'monthly'),
         kwargs.get('pay_date', str(date.today())), hours, rate,
         bonus, deductions, net, kwargs.get('status', 'paid'), kwargs.get('notes', ''))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_payroll(payroll_id):
    conn = get_db()
    conn.execute("DELETE FROM payroll WHERE id = ?", (payroll_id,))
    conn.commit()
    conn.close()
    return True
