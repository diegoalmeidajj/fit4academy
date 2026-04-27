"""Member-only endpoints. Mounted under /api/v1/me/*.

Auth: requires JWT with sub_type='member'.
"""

from datetime import datetime, date, timedelta

from flask import jsonify, request

import models

from . import api_v1
from .auth import jwt_required, current_subject


# ───────────────────────── helpers ─────────────────────────

def _safe(call, default=None):
    try:
        return call()
    except Exception as e:
        print(f"[member api] {call.__name__ if hasattr(call,'__name__') else 'call'}: {e}")
        return default


def _membership_status(member, payments):
    """Return dict { state: 'active'|'late'|'expired'|'unknown', days_late: int, next_due: 'YYYY-MM-DD'|null }."""
    today = date.today()
    # Find a pending or due payment
    pending = [p for p in (payments or []) if p.get('status') == 'pending']
    if pending:
        # If any has a due_date in the past, late
        late_days = 0
        next_due_str = None
        for p in pending:
            d = p.get('due_date') or p.get('payment_date')
            if not d:
                continue
            try:
                ds = str(d)[:10]
                dt = datetime.strptime(ds, '%Y-%m-%d').date()
            except Exception:
                continue
            if dt < today:
                late_days = max(late_days, (today - dt).days)
            else:
                if next_due_str is None or ds < next_due_str:
                    next_due_str = ds
        if late_days > 0:
            return {'state': 'late', 'days_late': late_days, 'next_due': next_due_str}
        return {'state': 'active', 'days_late': 0, 'next_due': next_due_str}

    # Otherwise rely on member status field
    raw = (member.get('membership_status') or '').lower()
    if raw in ('active', 'paid'):
        return {'state': 'active', 'days_late': 0, 'next_due': None}
    if raw in ('expired', 'inactive'):
        return {'state': 'expired', 'days_late': 0, 'next_due': None}
    return {'state': 'unknown', 'days_late': 0, 'next_due': None}


# ───────────────────────── dashboard ─────────────────────────

@api_v1.route('/me/dashboard', methods=['GET'])
@jwt_required(role='member')
def member_dashboard():
    _, member_id = current_subject()
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member

    academy = _safe(lambda: models.get_academy_by_id(member.get('academy_id')))
    academy = dict(academy) if academy else None

    payments = _safe(lambda: models.get_payments_by_member(member_id), default=[]) or []
    membership_status = _membership_status(member, payments)

    checkins = _safe(lambda: models.get_checkins_by_member(member_id, limit=10), default=[]) or []
    last_checkin = checkins[0] if checkins else None

    # Total check-ins
    total_checkins = _safe(lambda: len(models.get_checkins_by_member(member_id, limit=9999)), default=0)

    return jsonify({
        'member': {
            'id': member.get('id'),
            'first_name': member.get('first_name', ''),
            'last_name': member.get('last_name', ''),
            'photo_url': member.get('photo', ''),
            'belt': member.get('belt_name') or member.get('belt') or 'White',
            'belt_color': member.get('belt_color') or '#ffffff',
            'stripes': member.get('stripes', 0) or 0,
            'email': member.get('email', ''),
            'phone': member.get('phone', ''),
        },
        'academy': {
            'id': (academy or {}).get('id'),
            'name': (academy or {}).get('name', ''),
            'logo_url': (academy or {}).get('logo_url', ''),
            'primary_color': (academy or {}).get('portal_primary_color') or '#00DC82',
            'lat': (academy or {}).get('lat') or 0,
            'lng': (academy or {}).get('lng') or 0,
            'geofence_radius': (academy or {}).get('geofence_radius') or 100,
            'language': (academy or {}).get('language', 'en'),
        } if academy else None,
        'membership': membership_status,
        'last_checkin': {
            'id': last_checkin.get('id'),
            'created_at': str(last_checkin.get('created_at', ''))[:19],
            'class_name': last_checkin.get('class_name', ''),
            'method': last_checkin.get('method', ''),
        } if last_checkin else None,
        'total_checkins': total_checkins,
    })


# ───────────────────────── check-ins ─────────────────────────

ALLOWED_METHODS = {'manual', 'geofence', 'biometric', 'qr'}


@api_v1.route('/me/checkins', methods=['GET'])
@jwt_required(role='member')
def member_checkins_list():
    _, member_id = current_subject()
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
    except ValueError:
        limit = 50
    rows = _safe(lambda: models.get_checkins_by_member(member_id, limit=limit), default=[]) or []
    out = []
    for r in rows:
        d = r if isinstance(r, dict) else dict(r)
        out.append({
            'id': d.get('id'),
            'created_at': str(d.get('created_at', ''))[:19],
            'class_name': d.get('class_name', ''),
            'method': d.get('method', ''),
        })
    return jsonify({'items': out, 'count': len(out)})


@api_v1.route('/me/checkins', methods=['POST'])
@jwt_required(role='member')
def member_checkin_create():
    _, member_id = current_subject()
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member

    data = request.get_json(silent=True) or {}
    method = (data.get('method') or 'manual').strip()
    if method not in ALLOWED_METHODS:
        return jsonify({'error': 'invalid_method', 'allowed': sorted(ALLOWED_METHODS)}), 400
    class_id = data.get('class_id')

    # Anti-spam: don't allow more than 1 check-in per minute per member
    recent = _safe(lambda: models.get_checkins_by_member(member_id, limit=1), default=[]) or []
    if recent:
        try:
            last = recent[0]
            last_dt = datetime.strptime(str(last.get('created_at', ''))[:19], '%Y-%m-%d %H:%M:%S')
            if (datetime.utcnow() - last_dt).total_seconds() < 60:
                return jsonify({'error': 'too_soon', 'message': 'You just checked in.'}), 429
        except Exception:
            pass

    new_id = _safe(lambda: models.create_checkin(
        member_id=member_id,
        class_id=class_id,
        academy_id=member.get('academy_id'),
        method=method,
    ))
    if not new_id:
        return jsonify({'error': 'create_failed'}), 500
    return jsonify({'success': True, 'id': new_id, 'method': method})


# ───────────────────────── geofence ─────────────────────────

@api_v1.route('/me/academy/geofence', methods=['GET'])
@jwt_required(role='member')
def member_academy_geofence():
    _, member_id = current_subject()
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member
    academy = _safe(lambda: models.get_academy_by_id(member.get('academy_id')))
    if not academy:
        return jsonify({'error': 'no_academy'}), 404
    academy = dict(academy)
    return jsonify({
        'academy_id': academy.get('id'),
        'name': academy.get('name', ''),
        'lat': academy.get('lat') or 0,
        'lng': academy.get('lng') or 0,
        'radius': academy.get('geofence_radius') or 100,
        'configured': bool(academy.get('lat') and academy.get('lng')),
    })


# ───────────────────────── biometric ─────────────────────────

@api_v1.route('/me/biometric', methods=['POST'])
@jwt_required(role='member')
def member_biometric_set():
    """Toggle biometric login for the current member's credential."""
    _, member_id = current_subject()
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled'))
    try:
        models.set_member_biometric_enabled(member_id, enabled)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'success': True, 'enabled': enabled})


@api_v1.route('/me/biometric', methods=['GET'])
@jwt_required(role='member')
def member_biometric_get():
    _, member_id = current_subject()
    cred = models.get_member_credential_by_member_id(member_id)
    return jsonify({'enabled': bool(cred and cred.get('biometric_enabled'))})


# ───────────────────────── profile update ─────────────────────────

@api_v1.route('/me', methods=['PATCH'])
@jwt_required(role='member')
def member_update_profile():
    """Allow member to update their own basic profile fields."""
    _, member_id = current_subject()
    data = request.get_json(silent=True) or {}
    allowed_fields = {'phone', 'address', 'city', 'state', 'zip_code', 'photo'}
    payload = {k: v for k, v in data.items() if k in allowed_fields}
    if not payload:
        return jsonify({'error': 'no_fields'}), 400
    try:
        ok = models.update_member(member_id, **payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'success': bool(ok)})


# ───────────────────────── schedule (classes) ─────────────────────────

DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


@api_v1.route('/me/schedule', methods=['GET'])
@jwt_required(role='member')
def member_schedule():
    """Return next 7 days of classes at the member's academy, grouped by day."""
    _, member_id = current_subject()
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member
    academy_id = member.get('academy_id') or 1

    today = date.today()
    days = []
    for offset in range(7):
        d = today + timedelta(days=offset)
        # Python: Monday=0..Sunday=6;  schedule day_of_week: 0=Sun..6=Sat (commonly).
        # Many seed DBs use 0=Sunday convention. Use d.weekday() which is Mon=0..Sun=6,
        # and convert: dow = (d.weekday() + 1) % 7  -> 0=Sun..6=Sat.
        dow = (d.weekday() + 1) % 7
        rows = _safe(lambda dow=dow: models.get_schedule_by_day(dow, academy_id), default=[]) or []
        items = []
        for r in rows:
            x = r if isinstance(r, dict) else dict(r)
            items.append({
                'class_id': x.get('class_id'),
                'name': x.get('class_name', ''),
                'instructor': x.get('instructor', ''),
                'class_type': x.get('class_type', ''),
                'start_time': x.get('start_time', ''),
                'end_time': x.get('end_time', ''),
                'duration': x.get('duration'),
            })
        days.append({
            'date': d.isoformat(),
            'day_label': DAY_NAMES[dow],
            'is_today': offset == 0,
            'classes': items,
        })
    return jsonify({'days': days})


# ───────────────────────── events (competitions) ─────────────────────────

@api_v1.route('/me/events', methods=['GET'])
@jwt_required(role='member')
def member_events():
    """List upcoming events at the academy."""
    _, member_id = current_subject()
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member
    academy_id = member.get('academy_id') or 1
    rows = _safe(lambda: models.get_all_events(academy_id), default=[]) or []
    today_str = date.today().isoformat()
    out = []
    for r in rows:
        x = r if isinstance(r, dict) else dict(r)
        d = str(x.get('event_date') or '')[:10]
        # Show today + future only
        if d and d < today_str:
            continue
        out.append({
            'id': x.get('id'),
            'title': x.get('title') or x.get('name', ''),
            'description': x.get('description', ''),
            'event_date': d,
            'event_time': x.get('event_time', ''),
            'location': x.get('location', ''),
            'photo': x.get('photo', ''),
            'event_type': x.get('event_type', ''),
            'price': x.get('price', 0) or 0,
            'landing_url': f"/event/{x.get('id')}" if x.get('id') else '',
        })
    out.sort(key=lambda e: (e['event_date'] or '9999-12-31', e['event_time'] or ''))
    return jsonify({'items': out, 'count': len(out)})


# ───────────────────────── payments ─────────────────────────

@api_v1.route('/me/payments', methods=['GET'])
@jwt_required(role='member')
def member_payments_list():
    _, member_id = current_subject()
    rows = _safe(lambda: models.get_payments_by_member(member_id), default=[]) or []
    out = []
    for r in rows:
        x = r if isinstance(r, dict) else dict(r)
        out.append({
            'id': x.get('id'),
            'amount': x.get('amount', 0) or 0,
            'status': x.get('status', ''),
            'method': x.get('method', ''),
            'reference': x.get('reference', ''),
            'notes': x.get('notes', ''),
            'payment_date': str(x.get('payment_date') or '')[:10],
            'due_date': str(x.get('due_date') or '')[:10] if x.get('due_date') else None,
        })
    # Most recent first
    out.sort(key=lambda p: p['payment_date'] or '', reverse=True)
    return jsonify({'items': out, 'count': len(out)})


# ───────────────────────── promotion requests ─────────────────────────

@api_v1.route('/me/promotion-requests', methods=['GET'])
@jwt_required(role='member')
def member_promotion_requests_list():
    _, member_id = current_subject()
    rows = _safe(lambda: models.get_promotion_requests_by_member(member_id), default=[]) or []
    out = []
    for r in rows:
        out.append({
            'id': r.get('id'),
            'requested_belt': r.get('requested_belt'),
            'requested_stripes': r.get('requested_stripes'),
            'current_belt': r.get('current_belt'),
            'current_stripes': r.get('current_stripes'),
            'message': r.get('message', ''),
            'status': r.get('status', 'pending'),
            'decision_note': r.get('decision_note', ''),
            'created_at': str(r.get('created_at', ''))[:19],
            'decided_at': str(r.get('decided_at', ''))[:19] if r.get('decided_at') else None,
        })
    return jsonify({'items': out})


@api_v1.route('/me/promotion-requests', methods=['POST'])
@jwt_required(role='member')
def member_promotion_request_create():
    _, member_id = current_subject()
    data = request.get_json(silent=True) or {}
    requested_belt = (data.get('requested_belt') or '').strip()
    try:
        requested_stripes = int(data.get('requested_stripes') or 0)
    except Exception:
        requested_stripes = 0
    message = (data.get('message') or '').strip()[:1000]

    if not requested_belt and requested_stripes <= 0:
        return jsonify({'error': 'requested_belt_or_stripes_required'}), 400

    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member

    # Block multiple pending requests
    existing = _safe(lambda: models.get_promotion_requests_by_member(member_id, limit=5), default=[]) or []
    for r in existing:
        if r.get('status') == 'pending':
            return jsonify({'error': 'pending_request_exists',
                            'message': 'You already have a pending request. Wait for the coach to respond.'}), 409

    new_id = _safe(lambda: models.create_promotion_request(
        member_id=member_id,
        academy_id=member.get('academy_id') or 1,
        current_belt=member.get('belt_name') or member.get('belt') or '',
        current_stripes=member.get('stripes', 0) or 0,
        requested_belt=requested_belt,
        requested_stripes=requested_stripes,
        message=message,
    ))
    if not new_id:
        return jsonify({'error': 'create_failed'}), 500

    # Notify staff in admin web /notifications inbox
    member_name = (member.get('first_name', '') + ' ' + member.get('last_name', '')).strip()
    target = requested_belt or f"{requested_stripes} stripes"
    _safe(lambda: models.create_notification(
        academy_id=member.get('academy_id') or 1,
        member_id=member_id,
        notification_type='promotion_request',
        title=f"{member_name or 'A member'} requested promotion",
        message=f"Wants {target}." + (f" Note: \"{message[:140]}\"" if message else ''),
    ))

    # Best-effort push to staff device
    try:
        import notifications_lib
        owner_id = None
        academy = _safe(lambda: models.get_academy_by_id(member.get('academy_id') or 1))
        if academy:
            owner_id = (dict(academy) if not isinstance(academy, dict) else academy).get('owner_id')
        if owner_id:
            notifications_lib.send_push(
                'staff', owner_id,
                'New promotion request',
                f"{member.get('first_name','')} requested promotion to {requested_belt or 'next stripe'}.",
                data={'type': 'promotion_request', 'id': new_id},
            )
    except Exception:
        pass

    return jsonify({'success': True, 'id': new_id})


# ───────────────────────── chat (member side) ─────────────────────────

@api_v1.route('/me/chat/messages', methods=['GET'])
@jwt_required(role='member')
def member_chat_list():
    _, member_id = current_subject()
    rows = _safe(lambda: models.get_chat_messages(member_id, limit=200), default=[]) or []
    out = []
    for r in rows:
        out.append({
            'id': r.get('id'),
            'sender_type': r.get('sender_type'),
            'body': r.get('body', ''),
            'created_at': str(r.get('created_at', ''))[:19],
            'read_at': str(r.get('read_at', ''))[:19] if r.get('read_at') else None,
        })
    # Mark staff messages as read by this member
    _safe(lambda: models.mark_chat_read(member_id, 'member'))
    return jsonify({'items': out})


@api_v1.route('/me/chat/messages', methods=['POST'])
@jwt_required(role='member')
def member_chat_send():
    _, member_id = current_subject()
    data = request.get_json(silent=True) or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'body_required'}), 400
    if len(body) > 4000:
        return jsonify({'error': 'too_long'}), 400

    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member

    new_id = _safe(lambda: models.create_chat_message(
        academy_id=member.get('academy_id') or 1,
        member_id=member_id,
        sender_type='member',
        sender_id=member_id,
        body=body,
    ))
    if not new_id:
        return jsonify({'error': 'create_failed'}), 500

    # NOTE: We deliberately do NOT call create_notification() here. Chat threads
    # are surfaced to staff as an aggregated "Conversations" section in the
    # /notifications inbox (one row per member, not one per message), so we'd
    # only end up with duplicate noise.
    member_name = (member.get('first_name', '') + ' ' + member.get('last_name', '')).strip()
    preview = body[:160] + ('…' if len(body) > 160 else '')

    # Best-effort push to staff device (still useful so they get a phone alert)
    try:
        import notifications_lib
        academy = _safe(lambda: models.get_academy_by_id(member.get('academy_id') or 1))
        owner_id = None
        if academy:
            owner_id = (dict(academy) if not isinstance(academy, dict) else academy).get('owner_id')
        if owner_id:
            notifications_lib.send_push(
                'staff', owner_id,
                f"Message from {member.get('first_name', 'a member')}",
                preview,
                data={'type': 'chat', 'member_id': member_id, 'message_id': new_id},
            )
    except Exception:
        pass

    return jsonify({'success': True, 'id': new_id})
