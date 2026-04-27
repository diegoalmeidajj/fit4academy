"""Email + SMS delivery helpers.

Reads SMTP and Twilio credentials from environment. Each helper returns
(ok: bool, error: str | None) so callers can surface delivery status.
"""

import os


def _smtp_config():
    return {
        'host': os.environ.get('SMTP_HOST', '').strip(),
        'port': int(os.environ.get('SMTP_PORT', '587') or 587),
        'user': os.environ.get('SMTP_USER', '').strip(),
        'password': os.environ.get('SMTP_PASS', ''),
        'sender': os.environ.get('SMTP_FROM', '').strip() or os.environ.get('SMTP_USER', '').strip(),
    }


def _twilio_config():
    # Accept both naming conventions (legacy: SID/TOKEN/FROM, .env.example: ACCOUNT_SID/AUTH_TOKEN/PHONE)
    return {
        'sid': (os.environ.get('TWILIO_ACCOUNT_SID') or os.environ.get('TWILIO_SID') or '').strip(),
        'token': (os.environ.get('TWILIO_AUTH_TOKEN') or os.environ.get('TWILIO_TOKEN') or '').strip(),
        'sender': (os.environ.get('TWILIO_PHONE') or os.environ.get('TWILIO_FROM') or '').strip(),
    }


def email_configured():
    cfg = _smtp_config()
    return bool(cfg['host'] and cfg['user'])


def sms_configured():
    cfg = _twilio_config()
    return bool(cfg['sid'] and cfg['token'] and cfg['sender'])


def send_email(to_address, subject, body, html_body=None):
    """Send a single email. Returns (ok, error)."""
    if not to_address:
        return False, 'Missing recipient'

    cfg = _smtp_config()
    if not (cfg['host'] and cfg['user']):
        return False, 'SMTP is not configured'

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = cfg['sender']
        msg['To'] = to_address
        msg['Subject'] = subject or ''
        msg.attach(MIMEText(body or '', 'plain'))
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(cfg['host'], cfg['port'], timeout=15)
        try:
            server.starttls()
            server.login(cfg['user'], cfg['password'])
            server.sendmail(cfg['sender'], to_address, msg.as_string())
        finally:
            try:
                server.quit()
            except Exception:
                pass
        return True, None
    except Exception as e:
        print(f"[notifications] Email send failed for {to_address}: {e}")
        return False, str(e)


def send_sms(to_phone, body):
    """Send a single SMS via Twilio. Returns (ok, error)."""
    if not to_phone:
        return False, 'Missing recipient'

    cfg = _twilio_config()
    if not (cfg['sid'] and cfg['token'] and cfg['sender']):
        return False, 'Twilio is not configured'

    try:
        from twilio.rest import Client
    except ImportError:
        return False, 'twilio package not installed'

    try:
        client = Client(cfg['sid'], cfg['token'])
        client.messages.create(body=body, from_=cfg['sender'], to=to_phone)
        return True, None
    except Exception as e:
        print(f"[notifications] SMS send failed for {to_phone}: {e}")
        return False, str(e)


# ───────────────────── Expo Push Notifications ─────────────────────

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def send_push(owner_type, owner_id, title, body, data=None):
    """Send a push notification to all device tokens for a member or staff user.

    owner_type: 'member' or 'staff'
    owner_id:   row id
    Returns (sent_count, errors_list).
    """
    import requests
    import models

    if owner_type not in ('member', 'staff'):
        return 0, ['invalid owner_type']

    tokens = models.list_device_tokens_for_owner(owner_type, owner_id) or []
    if not tokens:
        return 0, []

    messages = []
    for tok in tokens:
        msg = {
            'to': tok,
            'sound': 'default',
            'title': title or '',
            'body': body or '',
        }
        if data:
            msg['data'] = data
        messages.append(msg)

    sent = 0
    errors = []
    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return 0, [f"HTTP {resp.status_code}: {resp.text[:200]}"]
        body = resp.json()
        receipts = body.get('data') or []
        if not isinstance(receipts, list):
            receipts = [receipts]
        for tok, receipt in zip(tokens, receipts):
            if receipt.get('status') == 'ok':
                sent += 1
                continue
            details = receipt.get('details') or {}
            err_code = details.get('error') or receipt.get('message') or 'unknown'
            errors.append(f"{tok}: {err_code}")
            # Drop dead tokens so we don't keep retrying
            if err_code in ('DeviceNotRegistered', 'InvalidCredentials'):
                try:
                    models.remove_device_token(tok)
                except Exception:
                    pass
    except Exception as e:
        return sent, errors + [str(e)]

    return sent, errors

