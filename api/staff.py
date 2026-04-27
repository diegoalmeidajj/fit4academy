"""Staff-only endpoints. Mounted under /api/v1/staff/*.

Auth: JWT with sub_type='staff'.
"""

from flask import jsonify, request

import models

from . import api_v1
from .auth import jwt_required, current_subject


def _staff_academy_id(user_id):
    user = models.get_user_by_id(user_id)
    if not user:
        return None
    user = dict(user) if not isinstance(user, dict) else user
    return user.get('academy_id') or 1


def _safe(call, default=None):
    try:
        return call()
    except Exception as e:
        print(f"[staff api] {e}")
        return default


# ───────────────────────── promotion requests ─────────────────────────

@api_v1.route('/staff/promotion-requests', methods=['GET'])
@jwt_required(role='staff')
def staff_promotion_requests_list():
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    if academy_id is None:
        return jsonify({'error': 'no_academy'}), 400
    status = request.args.get('status')
    rows = _safe(lambda: models.get_promotion_requests_for_academy(academy_id, status), default=[]) or []
    out = []
    for r in rows:
        out.append({
            'id': r.get('id'),
            'member_id': r.get('member_id'),
            'first_name': r.get('first_name', ''),
            'last_name': r.get('last_name', ''),
            'photo_url': r.get('photo_url', ''),
            'current_belt': r.get('current_belt'),
            'current_stripes': r.get('current_stripes'),
            'requested_belt': r.get('requested_belt'),
            'requested_stripes': r.get('requested_stripes'),
            'message': r.get('message', ''),
            'status': r.get('status'),
            'decision_note': r.get('decision_note', ''),
            'created_at': str(r.get('created_at', ''))[:19],
            'decided_at': str(r.get('decided_at', ''))[:19] if r.get('decided_at') else None,
        })
    return jsonify({'items': out})


@api_v1.route('/staff/promotion-requests/<int:req_id>/decide', methods=['POST'])
@jwt_required(role='staff')
def staff_promotion_request_decide(req_id):
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    note = (data.get('note') or '').strip()[:500]
    if status not in ('approved', 'rejected'):
        return jsonify({'error': 'invalid_status'}), 400

    req = _safe(lambda: models.get_promotion_request_by_id(req_id))
    if not req:
        return jsonify({'error': 'not_found'}), 404
    if req.get('academy_id') != academy_id:
        return jsonify({'error': 'forbidden'}), 403
    if req.get('status') != 'pending':
        return jsonify({'error': 'already_decided'}), 409

    ok = _safe(lambda: models.decide_promotion_request(req_id, user_id, status, note), default=False)
    if not ok:
        return jsonify({'error': 'decide_failed'}), 500

    # If approved, update the member's belt + stripes
    if status == 'approved':
        try:
            update = {}
            if req.get('requested_belt'):
                update['belt_name'] = req['requested_belt']
            if req.get('requested_stripes') is not None:
                update['stripes'] = req['requested_stripes']
            if update:
                _safe(lambda: models.update_member(req['member_id'], **update))
        except Exception:
            pass

    # Notify the member
    try:
        import notifications_lib
        member_id = req.get('member_id')
        title = 'Promotion approved! 🥋' if status == 'approved' else 'Promotion request reviewed'
        body = (
            f"You're now {req.get('requested_belt') or 'promoted'}! Congrats."
            if status == 'approved'
            else f"Your coach reviewed the request. {note or 'Talk to them on the mat.'}"
        )
        if member_id:
            notifications_lib.send_push('member', member_id, title, body,
                data={'type': 'promotion_decision', 'status': status})
    except Exception:
        pass

    return jsonify({'success': True, 'status': status})


# ───────────────────────── chat (staff side) ─────────────────────────

@api_v1.route('/staff/chat/threads', methods=['GET'])
@jwt_required(role='staff')
def staff_chat_threads():
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    if academy_id is None:
        return jsonify({'error': 'no_academy'}), 400
    rows = _safe(lambda: models.get_chat_threads_for_academy(academy_id, limit=100), default=[]) or []
    out = []
    for r in rows:
        out.append({
            'member_id': r.get('member_id'),
            'first_name': r.get('first_name', ''),
            'last_name': r.get('last_name', ''),
            'photo_url': r.get('photo_url', ''),
            'last_message': r.get('body', ''),
            'last_sender': r.get('sender_type'),
            'last_at': str(r.get('created_at', ''))[:19],
            'unread': r.get('sender_type') == 'member' and not r.get('read_at'),
        })
    return jsonify({'items': out})


@api_v1.route('/staff/chat/<int:member_id>/messages', methods=['GET'])
@jwt_required(role='staff')
def staff_chat_messages_list(member_id):
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
    member = models.get_member_by_id(member_id)
    if not member:
        return jsonify({'error': 'not_found'}), 404
    member = dict(member) if not isinstance(member, dict) else member
    if member.get('academy_id') != academy_id:
        return jsonify({'error': 'forbidden'}), 403
    rows = _safe(lambda: models.get_chat_messages(member_id), default=[]) or []
    out = []
    for r in rows:
        out.append({
            'id': r.get('id'),
            'sender_type': r.get('sender_type'),
            'body': r.get('body', ''),
            'created_at': str(r.get('created_at', ''))[:19],
            'read_at': str(r.get('read_at', ''))[:19] if r.get('read_at') else None,
        })
    _safe(lambda: models.mark_chat_read(member_id, 'staff'))
    return jsonify({'items': out, 'member': {
        'id': member.get('id'),
        'first_name': member.get('first_name', ''),
        'last_name': member.get('last_name', ''),
        'photo_url': member.get('photo_url', ''),
    }})


@api_v1.route('/staff/chat/<int:member_id>/messages', methods=['POST'])
@jwt_required(role='staff')
def staff_chat_send(member_id):
    _, user_id = current_subject()
    academy_id = _staff_academy_id(user_id)
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
    if member.get('academy_id') != academy_id:
        return jsonify({'error': 'forbidden'}), 403

    new_id = _safe(lambda: models.create_chat_message(
        academy_id=academy_id,
        member_id=member_id,
        sender_type='staff',
        sender_id=user_id,
        body=body,
    ))
    if not new_id:
        return jsonify({'error': 'create_failed'}), 500

    # Notify the member
    try:
        import notifications_lib
        preview = body[:80] + ('…' if len(body) > 80 else '')
        notifications_lib.send_push(
            'member', member_id,
            f"Message from your coach",
            preview,
            data={'type': 'chat', 'message_id': new_id},
        )
    except Exception:
        pass

    return jsonify({'success': True, 'id': new_id})
