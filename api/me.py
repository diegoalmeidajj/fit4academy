"""GET /api/v1/me — current authenticated subject."""

from flask import jsonify

import models

from . import api_v1
from .auth import jwt_required, current_subject


def _enrich_belt(member):
    """Return belt + stripes, falling back gracefully if columns are missing."""
    belt = member.get('belt_name') or member.get('belt') or 'White'
    stripes = member.get('stripes') if 'stripes' in member else 0
    return belt, stripes


@api_v1.route('/me', methods=['GET'])
@jwt_required()
def me():
    sub_type, sub_id = current_subject()
    if sub_type == 'member':
        member = models.get_member_by_id(sub_id)
        if not member:
            return jsonify({'error': 'not_found'}), 404
        member = dict(member) if not isinstance(member, dict) else member
        academy = None
        try:
            academy = models.get_academy_by_id(member.get('academy_id'))
        except Exception:
            pass
        academy = dict(academy) if academy else None
        belt, stripes = _enrich_belt(member)
        return jsonify({
            'type': 'member',
            'id': member.get('id'),
            'first_name': member.get('first_name', ''),
            'last_name': member.get('last_name', ''),
            'email': member.get('email', ''),
            'phone': member.get('phone', ''),
            'photo_url': member.get('photo_url', ''),
            'belt': belt,
            'stripes': stripes,
            'membership_status': member.get('membership_status', ''),
            'academy': {
                'id': (academy or {}).get('id'),
                'name': (academy or {}).get('name', ''),
                'logo_url': (academy or {}).get('logo_url', ''),
                'primary_color': (academy or {}).get('portal_primary_color', '#00DC82'),
                'language': (academy or {}).get('language', 'en'),
            } if academy else None,
        })

    if sub_type == 'staff':
        user = models.get_user_by_id(sub_id)
        if not user:
            return jsonify({'error': 'not_found'}), 404
        user = dict(user) if not isinstance(user, dict) else user
        academy = None
        try:
            academy = models.get_academy_by_id(user.get('academy_id'))
        except Exception:
            pass
        academy = dict(academy) if academy else None
        return jsonify({
            'type': 'staff',
            'id': user.get('id'),
            'username': user.get('username', ''),
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'role': user.get('role', 'user'),
            'photo_url': user.get('photo_url', ''),
            'academy': {
                'id': (academy or {}).get('id'),
                'name': (academy or {}).get('name', ''),
                'logo_url': (academy or {}).get('logo_url', ''),
                'language': (academy or {}).get('language', 'en'),
                'currency': (academy or {}).get('currency', 'USD'),
            } if academy else None,
        })

    return jsonify({'error': 'unknown_subject'}), 400
