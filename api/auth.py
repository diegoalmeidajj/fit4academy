"""Authentication endpoints + JWT helpers for the mobile API."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import jsonify, request

import config
import models

from . import api_v1

ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)
ALGO = 'HS256'


# ───────────────────────── token helpers ─────────────────────────

def _now():
    return datetime.now(timezone.utc)


def issue_token(subject_type, subject_id, kind='access', extra=None):
    """Issue a signed JWT.

    subject_type: 'member' or 'staff'
    subject_id:   row id from the corresponding table
    kind:         'access' or 'refresh'
    """
    ttl = ACCESS_TTL if kind == 'access' else REFRESH_TTL
    payload = {
        'sub_type': subject_type,
        'sub_id': subject_id,
        'kind': kind,
        'iat': int(_now().timestamp()),
        'exp': int((_now() + ttl).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, config.SECRET_KEY, algorithm=ALGO)


def decode_token(token):
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[ALGO])
    except jwt.ExpiredSignatureError:
        return {'_error': 'expired'}
    except jwt.InvalidTokenError:
        return {'_error': 'invalid'}


def _bearer_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None


def jwt_required(role=None):
    """Decorator: require a valid access token.

    role=None       — accept any authenticated subject (member or staff)
    role='member'   — only members
    role='staff'    — only staff/admin
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tok = _bearer_token()
            if not tok:
                return jsonify({'error': 'missing_token'}), 401
            payload = decode_token(tok)
            if payload.get('_error'):
                return jsonify({'error': payload['_error']}), 401
            if payload.get('kind') != 'access':
                return jsonify({'error': 'wrong_token_kind'}), 401
            sub_type = payload.get('sub_type')
            if role and sub_type != role:
                return jsonify({'error': 'forbidden'}), 403
            request.jwt = payload  # stash on request for handler use
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_subject():
    """Return (sub_type, sub_id) of the JWT attached to the request, if any."""
    payload = getattr(request, 'jwt', None)
    if not payload:
        return (None, None)
    return (payload.get('sub_type'), payload.get('sub_id'))


def _token_pair(sub_type, sub_id):
    return {
        'access_token': issue_token(sub_type, sub_id, 'access'),
        'refresh_token': issue_token(sub_type, sub_id, 'refresh'),
        'token_type': 'Bearer',
        'expires_in': int(ACCESS_TTL.total_seconds()),
    }


# ───────────────────────── endpoints ─────────────────────────

@api_v1.route('/auth/member/signup-with-pin', methods=['POST'])
def member_signup_with_pin():
    """First-time member account creation using the per-member PIN
    (the same PIN exposed in the member QR code on the gym side)."""
    data = request.get_json(silent=True) or {}
    pin = (data.get('pin') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not pin or not email or not password:
        return jsonify({'error': 'pin_email_password_required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'password_too_short'}), 400
    import re
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'invalid_email'}), 400

    # Find member by PIN. Prefer existing helper if present, else inline lookup.
    conn = models.get_db()
    try:
        row = conn.execute("SELECT * FROM members WHERE pin = ? AND active = ?", (pin, True)).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({'error': 'invalid_pin'}), 404
    member = dict(row)

    # Block creating a second credential for the same member
    if models.get_member_credential_by_member_id(member['id']):
        return jsonify({'error': 'already_registered'}), 409
    # Block email collision across members
    if models.get_member_credential_by_email(email):
        return jsonify({'error': 'email_in_use'}), 409

    cred_id = models.create_member_credential(member['id'], email, password)
    if not cred_id:
        return jsonify({'error': 'create_failed'}), 500

    return jsonify({
        'success': True,
        'member_id': member['id'],
        **_token_pair('member', member['id']),
    })


@api_v1.route('/auth/member/login', methods=['POST'])
def member_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({'error': 'email_password_required'}), 400
    member = models.authenticate_member(email, password)
    if not member:
        return jsonify({'error': 'invalid_credentials'}), 401
    return jsonify({
        'success': True,
        'member_id': member['id'],
        **_token_pair('member', member['id']),
    })


@api_v1.route('/auth/staff/login', methods=['POST'])
def staff_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'username_password_required'}), 400
    user = models.authenticate_user(username, password)
    if not user:
        return jsonify({'error': 'invalid_credentials'}), 401
    return jsonify({
        'success': True,
        'user_id': user['id'],
        'role': user.get('role', 'user'),
        **_token_pair('staff', user['id']),
    })


@api_v1.route('/auth/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json(silent=True) or {}
    rtok = (data.get('refresh_token') or '').strip()
    if not rtok:
        return jsonify({'error': 'refresh_token_required'}), 400
    payload = decode_token(rtok)
    if payload.get('_error'):
        return jsonify({'error': payload['_error']}), 401
    if payload.get('kind') != 'refresh':
        return jsonify({'error': 'wrong_token_kind'}), 401
    sub_type = payload.get('sub_type')
    sub_id = payload.get('sub_id')
    if not sub_type or not sub_id:
        return jsonify({'error': 'invalid_token'}), 401
    # Issue a fresh access token (refresh token kept the same; clients can request rotation later)
    return jsonify({
        'access_token': issue_token(sub_type, sub_id, 'access'),
        'token_type': 'Bearer',
        'expires_in': int(ACCESS_TTL.total_seconds()),
    })


@api_v1.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout is client-side (drop tokens). We optionally drop the device token here
    so push notifications stop reaching the device."""
    data = request.get_json(silent=True) or {}
    expo_token = (data.get('expo_token') or '').strip()
    if expo_token:
        try:
            models.remove_device_token(expo_token)
        except Exception:
            pass
    return jsonify({'success': True})


@api_v1.route('/auth/device-token', methods=['POST'])
@jwt_required()
def register_device_token():
    """Register/refresh the device's Expo Push Token for the authenticated subject."""
    data = request.get_json(silent=True) or {}
    expo_token = (data.get('expo_token') or '').strip()
    platform = (data.get('platform') or '').strip()  # 'ios' / 'android' / 'web'
    if not expo_token:
        return jsonify({'error': 'expo_token_required'}), 400
    sub_type, sub_id = current_subject()
    ok = models.register_device_token(sub_type, sub_id, expo_token, platform)
    if not ok:
        return jsonify({'error': 'register_failed'}), 500
    return jsonify({'success': True})
