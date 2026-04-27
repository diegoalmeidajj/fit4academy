"""Unified inbox helpers — thread + message persistence + channel routing.

The inbox aggregates conversations across SMS (Twilio), email (IMAP/SMTP),
Facebook Messenger, Instagram DM, WhatsApp Business, and the in-app member
chat. Each channel has its own webhook/poller; they all funnel into the
same `inbox_threads` + `inbox_messages` tables.

Channel kinds:
- 'app_chat'     — internal chat between staff and members in the PWA
- 'sms'          — SMS via Twilio
- 'email'        — Email via IMAP/SMTP
- 'fb_messenger' — Facebook Messenger
- 'ig_dm'        — Instagram DM
- 'whatsapp'     — WhatsApp Business via Meta Cloud API

Threads are matched to a member when possible (by phone number for SMS, by
email for email, by linked Meta page user ID for FB/IG). Otherwise the
thread is "unmatched" and a coach can manually link it to a member later.
"""

import json
from datetime import datetime

import models


CHANNEL_KINDS = ('app_chat', 'sms', 'email', 'fb_messenger', 'ig_dm', 'whatsapp')

CHANNEL_LABELS = {
    'app_chat': 'App chat',
    'sms': 'SMS',
    'email': 'Email',
    'fb_messenger': 'Messenger',
    'ig_dm': 'Instagram',
    'whatsapp': 'WhatsApp',
}

CHANNEL_ICONS = {
    'app_chat': 'bi-chat-dots',
    'sms': 'bi-phone',
    'email': 'bi-envelope',
    'fb_messenger': 'bi-messenger',
    'ig_dm': 'bi-instagram',
    'whatsapp': 'bi-whatsapp',
}

CHANNEL_COLORS = {
    'app_chat': '#00DC82',
    'sms': '#22d3ee',
    'email': '#94a3b8',
    'fb_messenger': '#0084ff',
    'ig_dm': '#E1306C',
    'whatsapp': '#25D366',
}


# ─── Threads ──────────────────────────────────────────────────────────

def upsert_thread(academy_id, channel_kind, contact_handle, contact_name='',
                  channel_id=None, external_thread_id='', member_id=None):
    """Find or create a thread for (channel_kind, contact_handle).

    Returns the thread_id. If a member with matching phone/email is found
    and member_id is None, links automatically.
    """
    if channel_kind not in CHANNEL_KINDS:
        raise ValueError(f"Unknown channel kind: {channel_kind}")

    conn = models.get_db()
    try:
        row = conn.execute(
            """SELECT id, member_id FROM inbox_threads
               WHERE academy_id = ? AND channel_kind = ? AND contact_handle = ?""",
            (academy_id, channel_kind, contact_handle)
        ).fetchone()

        if row:
            tid = (row['id'] if isinstance(row, dict) else row[0])
            existing_member = (row['member_id'] if isinstance(row, dict) else row[1])
            # Backfill member_id if we now have a match
            if not existing_member and member_id is None:
                member_id = _try_match_member(academy_id, channel_kind, contact_handle)
            if member_id and not existing_member:
                conn.execute("UPDATE inbox_threads SET member_id = ? WHERE id = ?",
                             (member_id, tid))
                conn.commit()
            return tid

        if member_id is None:
            member_id = _try_match_member(academy_id, channel_kind, contact_handle)

        cur = conn.execute(
            """INSERT INTO inbox_threads
               (academy_id, channel_id, channel_kind, contact_handle, contact_name,
                external_thread_id, member_id, last_message_at, unread_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (academy_id, channel_id, channel_kind, contact_handle, contact_name,
             external_thread_id, member_id, datetime.utcnow().isoformat(' ', 'seconds'))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _try_match_member(academy_id, channel_kind, contact_handle):
    """Match a contact handle to an existing member when possible."""
    if not contact_handle:
        return None
    handle = contact_handle.strip().lower()
    conn = models.get_db()
    try:
        if channel_kind in ('sms', 'whatsapp'):
            digits = ''.join(c for c in handle if c.isdigit())
            if digits:
                row = conn.execute(
                    "SELECT id FROM members WHERE academy_id = ? AND REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '+', '') LIKE ?",
                    (academy_id, f'%{digits[-10:]}')
                ).fetchone()
                if row:
                    return (row['id'] if isinstance(row, dict) else row[0])
        elif channel_kind == 'email':
            row = conn.execute(
                "SELECT id FROM members WHERE academy_id = ? AND LOWER(email) = ?",
                (academy_id, handle)
            ).fetchone()
            if row:
                return (row['id'] if isinstance(row, dict) else row[0])
    except Exception:
        pass
    finally:
        conn.close()
    return None


def add_message(thread_id, direction, body, attachment_url='', external_id='',
                sender_label='', ai_drafted=False):
    """Append a message to a thread + update thread metadata.

    direction='in' bumps unread_count; direction='out' resets it (we just replied).
    """
    if direction not in ('in', 'out'):
        raise ValueError(f"Bad direction: {direction}")

    conn = models.get_db()
    try:
        # De-dup by external_id when provided (webhook retries)
        if external_id:
            existing = conn.execute(
                "SELECT id FROM inbox_messages WHERE thread_id = ? AND external_id = ?",
                (thread_id, external_id)
            ).fetchone()
            if existing:
                return (existing['id'] if isinstance(existing, dict) else existing[0])

        cur = conn.execute(
            """INSERT INTO inbox_messages
               (thread_id, direction, body, attachment_url, external_id,
                sender_label, ai_drafted, sent_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (thread_id, direction, body, attachment_url, external_id,
             sender_label, bool(ai_drafted),
             datetime.utcnow().isoformat(' ', 'seconds'))
        )
        msg_id = cur.lastrowid

        preview = (body or '')[:160]
        if direction == 'in':
            conn.execute(
                """UPDATE inbox_threads SET
                   last_message_at = CURRENT_TIMESTAMP,
                   last_message_preview = ?,
                   unread_count = unread_count + 1
                   WHERE id = ?""",
                (preview, thread_id)
            )
        else:
            conn.execute(
                """UPDATE inbox_threads SET
                   last_message_at = CURRENT_TIMESTAMP,
                   last_message_preview = ?,
                   unread_count = 0
                   WHERE id = ?""",
                (preview, thread_id)
            )
        conn.commit()
        return msg_id
    finally:
        conn.close()


def list_threads(academy_id, kind=None, archived=False, limit=200):
    """Return threads ordered by last_message_at DESC."""
    conn = models.get_db()
    try:
        sql = """SELECT t.*, m.first_name, m.last_name, m.photo
                 FROM inbox_threads t
                 LEFT JOIN members m ON t.member_id = m.id
                 WHERE t.academy_id = ? AND t.archived = ?"""
        params = [academy_id, bool(archived)]
        if kind:
            sql += " AND t.channel_kind = ?"
            params.append(kind)
        sql += " ORDER BY t.last_message_at DESC NULLS LAST LIMIT ?"
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
        except Exception:
            # SQLite older versions don't support NULLS LAST — retry without.
            sql = sql.replace(" NULLS LAST", "")
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_thread(thread_id):
    conn = models.get_db()
    try:
        row = conn.execute(
            """SELECT t.*, m.first_name, m.last_name, m.photo, m.belt_rank_id, m.email AS member_email, m.phone AS member_phone
               FROM inbox_threads t
               LEFT JOIN members m ON t.member_id = m.id
               WHERE t.id = ?""",
            (thread_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_thread_messages(thread_id, limit=500):
    conn = models.get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM inbox_messages WHERE thread_id = ? ORDER BY sent_at ASC LIMIT ?",
            (thread_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_thread_read(thread_id):
    conn = models.get_db()
    try:
        now = datetime.utcnow().isoformat(' ', 'seconds')
        conn.execute(
            "UPDATE inbox_messages SET read_at = ? WHERE thread_id = ? AND direction = 'in' AND read_at IS NULL",
            (now, thread_id)
        )
        conn.execute("UPDATE inbox_threads SET unread_count = 0 WHERE id = ?", (thread_id,))
        conn.commit()
    finally:
        conn.close()


def archive_thread(thread_id, archived=True):
    conn = models.get_db()
    try:
        conn.execute("UPDATE inbox_threads SET archived = ? WHERE id = ?", (bool(archived), thread_id))
        conn.commit()
    finally:
        conn.close()


def link_thread_to_member(thread_id, member_id):
    conn = models.get_db()
    try:
        conn.execute("UPDATE inbox_threads SET member_id = ? WHERE id = ?", (member_id, thread_id))
        conn.commit()
    finally:
        conn.close()


def total_unread(academy_id):
    conn = models.get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(unread_count), 0) AS n FROM inbox_threads WHERE academy_id = ? AND archived = ?",
            (academy_id, False)
        ).fetchone()
        return int(row['n'] if isinstance(row, dict) else (row[0] or 0))
    finally:
        conn.close()


# ─── Channels ──────────────────────────────────────────────────────────

def list_channels(academy_id):
    conn = models.get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM inbox_channels WHERE academy_id = ? ORDER BY id",
            (academy_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d['config'] = json.loads(d.get('config_json') or '{}')
            except Exception:
                d['config'] = {}
            out.append(d)
        return out
    finally:
        conn.close()


def get_channel(channel_id):
    conn = models.get_db()
    try:
        row = conn.execute("SELECT * FROM inbox_channels WHERE id = ?", (channel_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d['config'] = json.loads(d.get('config_json') or '{}')
        except Exception:
            d['config'] = {}
        return d
    finally:
        conn.close()


def upsert_channel(academy_id, kind, name='', config=None, active=True):
    """Insert or update a channel by (academy_id, kind, name).

    For unique single-channel kinds (sms, email), we treat (academy_id, kind)
    as unique. For Meta channels there can be multiple pages so name is part
    of the key.
    """
    if kind not in CHANNEL_KINDS:
        raise ValueError(f"Unknown channel kind: {kind}")
    cfg = json.dumps(config or {})
    conn = models.get_db()
    try:
        if kind in ('sms', 'email'):
            existing = conn.execute(
                "SELECT id FROM inbox_channels WHERE academy_id = ? AND kind = ?",
                (academy_id, kind)
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM inbox_channels WHERE academy_id = ? AND kind = ? AND name = ?",
                (academy_id, kind, name)
            ).fetchone()
        if existing:
            cid = (existing['id'] if isinstance(existing, dict) else existing[0])
            conn.execute(
                "UPDATE inbox_channels SET name = ?, config_json = ?, active = ? WHERE id = ?",
                (name, cfg, bool(active), cid)
            )
            conn.commit()
            return cid
        cur = conn.execute(
            "INSERT INTO inbox_channels (academy_id, kind, name, config_json, active) VALUES (?, ?, ?, ?, ?)",
            (academy_id, kind, name, cfg, bool(active))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_channel(channel_id):
    conn = models.get_db()
    try:
        conn.execute("DELETE FROM inbox_channels WHERE id = ?", (channel_id,))
        conn.commit()
    finally:
        conn.close()


# ─── App-chat surfacing ────────────────────────────────────────────────

def send_via_meta(academy_id, channel_kind, recipient_id, body):
    """Send an outbound message via Meta Graph API.

    Uses the channel record's stored access_token and (for WhatsApp) the
    phone_number_id, or (for FB/IG) the page_id. Returns (ok: bool,
    error: str | None).

    Endpoints:
    - Messenger / Instagram Direct: POST /<page_id>/messages
    - WhatsApp Cloud API: POST /<phone_number_id>/messages
    """
    if channel_kind not in ('fb_messenger', 'ig_dm', 'whatsapp'):
        return False, f"Unsupported channel: {channel_kind}"
    if not recipient_id or not body:
        return False, "Missing recipient or body"

    chans = list_channels(academy_id)
    chan = next((c for c in chans if c.get('kind') == channel_kind and c.get('active')), None)
    if not chan:
        return False, f"No {channel_kind} channel configured."
    cfg = chan.get('config') or {}
    token = cfg.get('access_token')
    if not token:
        return False, "Channel access token missing."

    try:
        import requests
    except ImportError:
        return False, "requests library not installed."

    api_version = 'v19.0'

    try:
        if channel_kind == 'whatsapp':
            phone_number_id = cfg.get('phone_number_id')
            if not phone_number_id:
                return False, "WhatsApp phone_number_id missing."
            url = f'https://graph.facebook.com/{api_version}/{phone_number_id}/messages'
            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient_id,
                'type': 'text',
                'text': {'body': body},
            }
        else:
            # Messenger and Instagram Direct share the page-scoped Send API.
            page_id = cfg.get('page_id')
            if not page_id:
                return False, "Page ID missing."
            url = f'https://graph.facebook.com/{api_version}/{page_id}/messages'
            payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': body},
                'messaging_type': 'RESPONSE',
            }
            # IG vs FB is determined by which account the page is linked to —
            # the API endpoint shape is identical.

        r = requests.post(
            url,
            params={'access_token': token},
            json=payload,
            timeout=10,
        )
        if r.ok:
            return True, None
        try:
            err = r.json().get('error', {}).get('message', r.text[:200])
        except Exception:
            err = r.text[:200]
        return False, f'{r.status_code}: {err}'
    except requests.exceptions.RequestException as e:
        return False, f'Network error: {e}'
    except Exception as e:
        return False, f'Send error: {e}'


def sync_email_via_imap(academy_id):
    """Pull recent UNSEEN emails from the configured IMAP channel into the
    inbox. Returns (fetched, error) where error is None on success.

    This is invoked on-demand from the Channels page (Sync now button) to
    keep deployment simple — no background scheduler required. Each call
    marks fetched messages as Seen so we don't re-import.
    """
    import imaplib
    import email
    from email.header import decode_header

    chans = list_channels(academy_id)
    email_ch = next((c for c in chans if c.get('kind') == 'email' and c.get('active')), None)
    if not email_ch:
        return (0, 'No email channel configured.')
    cfg = email_ch.get('config') or {}
    host = cfg.get('imap_host', '').strip()
    user = cfg.get('imap_user', '').strip()
    pw = cfg.get('imap_pass', '').strip()
    if not (host and user and pw):
        return (0, 'IMAP host / user / password missing.')

    fetched = 0
    try:
        m = imaplib.IMAP4_SSL(host)
        m.login(user, pw)
        m.select('INBOX')
        typ, data = m.search(None, 'UNSEEN')
        if typ != 'OK':
            m.logout()
            return (0, f'IMAP search failed: {typ}')
        for num in (data[0].split() if data and data[0] else []):
            typ, raw = m.fetch(num, '(RFC822)')
            if typ != 'OK' or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            from_raw = msg.get('From', '')
            subj_raw = msg.get('Subject', '')
            ext_id = msg.get('Message-ID', '')

            def _decode(s):
                try:
                    parts = decode_header(s)
                    return ''.join(
                        (p.decode(c or 'utf-8', errors='replace') if isinstance(p, bytes) else p)
                        for p, c in parts
                    )
                except Exception:
                    return s

            from_addr = _decode(from_raw)
            subject = _decode(subj_raw)
            # Extract just the email address from "Name <email@x>"
            import re as _re
            mm = _re.search(r'<([^>]+)>', from_addr)
            handle = (mm.group(1) if mm else from_addr).strip().lower()

            body_text = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            body_text = part.get_payload(decode=True).decode(
                                part.get_content_charset() or 'utf-8',
                                errors='replace'
                            )
                            break
                        except Exception:
                            continue
            else:
                try:
                    body_text = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or 'utf-8', errors='replace'
                    )
                except Exception:
                    body_text = msg.get_payload() or ''

            preview = (subject + '\n\n' + body_text).strip()[:4000]
            tid = upsert_thread(
                academy_id=academy_id,
                channel_kind='email',
                contact_handle=handle,
                contact_name=from_addr,
                channel_id=email_ch.get('id'),
            )
            add_message(
                thread_id=tid,
                direction='in',
                body=preview,
                external_id=ext_id,
                sender_label=from_addr,
            )
            fetched += 1
        m.logout()
    except imaplib.IMAP4.error as e:
        return (fetched, f'IMAP error: {e}')
    except Exception as e:
        return (fetched, f'Error: {e}')

    return (fetched, None)


def sync_app_chat_threads(academy_id):
    """Mirror existing chat_messages threads into the unified inbox.

    Idempotent — running this twice doesn't duplicate threads. Each member
    with at least one chat_messages row gets a thread; new chat messages
    since last sync get added as inbox_messages. The original chat_messages
    table stays canonical for the PWA's /chat screen — this is purely a
    read-mirror so the staff can see app chat alongside SMS/email/etc.
    """
    conn = models.get_db()
    try:
        threads = conn.execute(
            """SELECT cm.member_id, m.first_name, m.last_name,
                      MAX(cm.id) AS last_id,
                      MAX(cm.created_at) AS last_at
               FROM chat_messages cm
               JOIN members m ON cm.member_id = m.id
               WHERE cm.academy_id = ?
               GROUP BY cm.member_id""",
            (academy_id,)
        ).fetchall()

        for t in threads:
            td = dict(t)
            handle = f"member-{td['member_id']}"
            tid = upsert_thread(
                academy_id=academy_id,
                channel_kind='app_chat',
                contact_handle=handle,
                contact_name=f"{td.get('first_name', '')} {td.get('last_name', '')}".strip(),
                member_id=td['member_id'],
            )
            # Fetch all chat_messages for this member that aren't already mirrored.
            existing_ext = {
                (m['external_id'] if isinstance(m, dict) else m[0])
                for m in conn.execute(
                    "SELECT external_id FROM inbox_messages WHERE thread_id = ?",
                    (tid,)
                ).fetchall()
            }
            msgs = conn.execute(
                "SELECT * FROM chat_messages WHERE member_id = ? ORDER BY id ASC",
                (td['member_id'],)
            ).fetchall()
            for m in msgs:
                md = dict(m)
                ext_id = f"chat-{md['id']}"
                if ext_id in existing_ext:
                    continue
                direction = 'in' if md.get('sender_type') == 'member' else 'out'
                add_message(
                    thread_id=tid,
                    direction=direction,
                    body=md.get('body', ''),
                    external_id=ext_id,
                    sender_label='Member' if direction == 'in' else 'Coach',
                )
    finally:
        conn.close()
