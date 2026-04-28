"""Lead capture endpoints.

Public: POST /api/v1/public/leads — anonymous submit from landing page or embed widget.
Staff:  GET /api/v1/staff/leads, PATCH /api/v1/staff/leads/<id> — gestor inbox.

A "lead" is persisted as a row in the existing `prospects` table.
"""

import time
from collections import deque

from flask import jsonify, request

import models

from . import api_v1
from .auth import jwt_required, current_subject


# ───────────────────────── rate limit (per-IP, in-memory) ─────────────────────────
# 10 submissions per IP per hour. Resets on process restart, which is fine for
# anti-spam — a determined attacker would still hit the captcha (added later).

_RATE_BUCKET = {}  # ip -> deque[timestamps]
_RATE_WINDOW_S = 3600
_RATE_MAX = 10


def _rate_limited(ip):
    now = time.time()
    bucket = _RATE_BUCKET.setdefault(ip, deque())
    while bucket and bucket[0] < now - _RATE_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX:
        return True
    bucket.append(now)
    return False


# ───────────────────────── helpers ─────────────────────────

def _staff_academy_id(user_id):
    user = models.get_user_by_id(user_id)
    if not user:
        return None
    user = dict(user) if not isinstance(user, dict) else user
    return user.get('academy_id') or 1


def _serialize_lead(p):
    return {
        'id': p.get('id'),
        'first_name': p.get('first_name', ''),
        'last_name': p.get('last_name', ''),
        'email': p.get('email', ''),
        'phone': p.get('phone', ''),
        'source': p.get('source', ''),
        'status': p.get('status', 'new'),
        'interested_in': p.get('interested_in', ''),
        'previous_experience': p.get('previous_experience', ''),
        'notes': p.get('notes', ''),
        'archived': bool(p.get('archived')),
        'created_at': str(p.get('created_at', ''))[:19],
        'updated_at': str(p.get('updated_at', ''))[:19],
    }


def _notify_new_lead(academy_id, prospect_id, lead):
    """Email gestor + push to all staff. Best-effort; failures are logged, not raised."""
    try:
        import notifications_lib
    except Exception as e:
        print(f"[leads] notifications_lib import failed: {e}")
        return

    full_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() or 'New lead'
    contact_bits = []
    if lead.get('email'):
        contact_bits.append(lead['email'])
    if lead.get('phone'):
        contact_bits.append(lead['phone'])
    contact_line = ' · '.join(contact_bits) or '(no contact info)'
    interest = lead.get('interested_in') or ''
    source = lead.get('source') or 'website'

    academy = None
    try:
        academy = models.get_academy_by_id(academy_id)
        academy = dict(academy) if academy and not isinstance(academy, dict) else academy
    except Exception:
        pass
    academy_name = (academy or {}).get('name', 'Your academy') if academy else 'Your academy'
    academy_email = (academy or {}).get('email', '') if academy else ''

    # Email the academy contact
    if academy_email:
        try:
            subject = f"New lead: {full_name}"
            body = (
                f"You have a new lead at {academy_name}.\n\n"
                f"Name: {full_name}\n"
                f"Contact: {contact_line}\n"
                f"Interested in: {interest or '—'}\n"
                f"Source: {source}\n\n"
                f"Open the app or /prospects to follow up."
            )
            notifications_lib.send_email(academy_email, subject, body)
        except Exception as e:
            print(f"[leads] email send failed: {e}")

    # Push every staff user with a registered device
    try:
        staff = models.list_staff_users_for_academy(academy_id) or []
        title = f"New lead — {full_name}"
        push_body = f"{contact_line} · {interest or source}"
        push_data = {'type': 'new_lead', 'prospect_id': prospect_id}
        for u in staff:
            uid = u.get('id') if isinstance(u, dict) else None
            if uid:
                try:
                    notifications_lib.send_push('staff', uid, title, push_body, data=push_data)
                except Exception as e:
                    print(f"[leads] push to staff {uid} failed: {e}")
    except Exception as e:
        print(f"[leads] staff fan-out failed: {e}")


# ───────────────────────── public capture ─────────────────────────

@api_v1.route('/public/leads', methods=['POST', 'OPTIONS'])
def public_lead_create():
    """Anonymous lead submission. CORS-friendly so the embed widget works
    from a third-party academy website."""
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp

    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '0.0.0.0').split(',')[0].strip()
    if _rate_limited(ip):
        resp = jsonify({'error': 'rate_limited'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 429

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    # Honeypot — bots fill hidden fields. Pretend success but discard.
    if (data.get('website_url') or data.get('company') or '').strip():
        resp = jsonify({'success': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    try:
        academy_id = int(data.get('academy_id') or 1)
    except (TypeError, ValueError):
        academy_id = 1

    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    full_name = (data.get('name') or '').strip()
    if not first_name and full_name:
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else last_name

    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()

    if not first_name:
        resp = jsonify({'error': 'first_name_required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400
    if not (email or phone):
        resp = jsonify({'error': 'contact_required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # Validate academy exists
    try:
        academy = models.get_academy_by_id(academy_id)
        if not academy:
            resp = jsonify({'error': 'academy_not_found'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp, 404
    except Exception as e:
        print(f"[leads] academy lookup failed: {e}")
        resp = jsonify({'error': 'lookup_failed'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    source = (data.get('source') or 'website')[:80]
    interested_in = (data.get('interested_in') or '')[:200]
    previous_experience = (data.get('previous_experience') or '')[:200]
    notes = (data.get('notes') or data.get('message') or '')[:1000]

    # Waiver — validate before creating prospect when academy requires it
    academy_dict = dict(academy) if not isinstance(academy, dict) else academy
    waiver_required = bool(academy_dict.get('waiver_required'))
    waiver_signature = (data.get('waiver_signature') or '').strip()
    waiver_accepted = bool(data.get('waiver_accepted'))
    if waiver_required:
        if not waiver_accepted or not waiver_signature:
            resp = jsonify({'error': 'waiver_required'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp, 400

    try:
        prospect_id = models.create_prospect(
            academy_id=academy_id,
            first_name=first_name[:100],
            last_name=last_name[:100],
            email=email[:200],
            phone=phone[:50],
            source=source,
            status='new',
            interested_in=interested_in,
            previous_experience=previous_experience,
            notes=notes,
        )
    except Exception as e:
        print(f"[leads] create_prospect failed: {e}")
        resp = jsonify({'error': 'create_failed'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    if not prospect_id:
        resp = jsonify({'error': 'create_failed'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    # Persist waiver acceptance (best-effort — failure shouldn't block lead).
    if waiver_required and waiver_signature:
        try:
            models.create_lead_waiver(
                academy_id=academy_id,
                prospect_id=prospect_id,
                signature_name=waiver_signature,
                waiver_text=academy_dict.get('waiver_text', '') or '',
                ip_address=ip,
                user_agent=request.headers.get('User-Agent', '')[:300],
            )
        except Exception as e:
            print(f"[leads] waiver persist failed: {e}")

    # Fire notifications (non-blocking would be nicer, but staying simple).
    _notify_new_lead(academy_id, prospect_id, {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'phone': phone,
        'source': source,
        'interested_in': interested_in,
    })

    resp = jsonify({'success': True, 'id': prospect_id})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# ───────────────────────── staff inbox ─────────────────────────

@api_v1.route('/staff/leads', methods=['GET'])
@jwt_required(role='staff')
def staff_leads_list():
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    if academy_id is None:
        return jsonify({'error': 'no_academy'}), 400

    status_filter = (request.args.get('status') or '').strip().lower()
    include_archived = request.args.get('include_archived') == '1'

    try:
        rows = models.get_all_prospects(academy_id) or []
    except Exception as e:
        print(f"[leads] list failed: {e}")
        rows = []

    items = []
    counts = {'new': 0, 'contacted': 0, 'qualified': 0, 'converted': 0, 'lost': 0, 'total': 0}
    for r in rows:
        if not include_archived and r.get('archived'):
            continue
        st = (r.get('status') or 'new').lower()
        counts['total'] += 1
        if st in counts:
            counts[st] += 1
        if status_filter and st != status_filter:
            continue
        items.append(_serialize_lead(r))

    return jsonify({'items': items, 'counts': counts})


@api_v1.route('/staff/leads/<int:lead_id>', methods=['PATCH'])
@jwt_required(role='staff')
def staff_lead_update(lead_id):
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    if academy_id is None:
        return jsonify({'error': 'no_academy'}), 400

    prospect = models.get_prospect_by_id(lead_id)
    if not prospect:
        return jsonify({'error': 'not_found'}), 404
    prospect = dict(prospect) if not isinstance(prospect, dict) else prospect
    if prospect.get('academy_id') != academy_id:
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(silent=True) or {}
    update = {}
    if 'status' in data:
        st = (data.get('status') or '').strip().lower()
        if st not in ('new', 'contacted', 'qualified', 'converted', 'lost'):
            return jsonify({'error': 'invalid_status'}), 400
        update['status'] = st
    if 'notes' in data:
        update['notes'] = (data.get('notes') or '')[:2000]
    if 'archived' in data:
        update['archived'] = bool(data.get('archived'))
    if 'follow_up_date' in data:
        update['follow_up_date'] = data.get('follow_up_date') or None

    if not update:
        return jsonify({'error': 'no_fields'}), 400

    try:
        models.update_prospect(lead_id, **update)
    except Exception as e:
        print(f"[leads] update failed: {e}")
        return jsonify({'error': 'update_failed'}), 500

    fresh = models.get_prospect_by_id(lead_id)
    fresh = dict(fresh) if fresh and not isinstance(fresh, dict) else (fresh or {})
    return jsonify({'success': True, 'lead': _serialize_lead(fresh)})
