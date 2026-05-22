import hmac
import hashlib
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, session
from models import db, WebhookLog, User, Video, push_notification

webhook_bp = Blueprint('webhook', __name__)

WEBHOOK_SECRET = 'whsec_dev_demo_key_2026'


def verify_signature(payload_bytes, signature_header):
    """HMAC-SHA256 signature verification."""
    if not signature_header:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def log_webhook(event_type, source, payload, valid, result=''):
    entry = WebhookLog(
        event_type=event_type,
        source=source,
        payload=payload,
        signature_valid=valid,
        processed=True,
        result=result,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


@webhook_bp.route('/webhook-dashboard')
def dashboard():
    logs = WebhookLog.query.order_by(WebhookLog.created_at.desc()).limit(50).all()
    return render_template('webhook.html', logs=logs, webhook_secret=WEBHOOK_SECRET)


@webhook_bp.route('/api/webhook/<event_type>', methods=['POST'])
def receive_webhook(event_type):
    """Universal webhook receiver. Third-party services POST here."""
    payload = request.get_json(force=True, silent=True) or {}
    raw = request.get_data()
    sig = request.headers.get('X-Webhook-Signature', '')
    valid = verify_signature(raw, sig)
    source = request.headers.get('X-Webhook-Source', 'unknown')

    result = ''
    try:
        if event_type == 'payment_completed':
            user_id = payload.get('user_id')
            coins = payload.get('coins', 0)
            if user_id and coins:
                user = db.session.get(User, int(user_id))
                if user:
                    user.coins_balance = (user.coins_balance or 0) + int(coins)
                    db.session.commit()
                    push_notification(user.id, None, 'coins',
                        f'Payment callback: +{coins} coins added',
                        '/settings')
                    result = f'Added {coins} coins to user {user_id}'

        elif event_type == 'video_ready':
            video_id = payload.get('video_id')
            user_id = payload.get('user_id')
            title = payload.get('title', '')
            if user_id:
                push_notification(int(user_id), None, 'video_ready',
                    f'Video "{title}" processing complete', f'/video/{video_id}')
                result = f'Notified user {user_id} about video {video_id}'

        elif event_type == 'comment_moderated':
            action = payload.get('action', '')
            comment_id = payload.get('comment_id', '')
            result = f'Moderation action "{action}" on comment {comment_id} logged'

        elif event_type == 'user_updated':
            user_id = payload.get('user_id')
            if payload.get('nickname') and user_id:
                user = db.session.get(User, int(user_id))
                if user:
                    user.bio = payload.get('nickname', user.bio)
                    db.session.commit()
                    result = f'Updated user {user_id} profile via webhook'

        else:
            result = f'Event type "{event_type}" received (no handler)'

    except Exception as e:
        result = f'Error: {str(e)}'

    log_webhook(event_type, source, payload, valid, result)
    return jsonify({'status': 'ok', 'result': result})


@webhook_bp.route('/api/webhook/simulate', methods=['POST'])
def simulate_webhook():
    """Simulate sending a webhook to our own receiver."""
    data = request.get_json() or {}
    event_type = data.get('event_type', 'payment_completed')
    payload = data.get('payload', {})

    import requests
    try:
        url = f'{request.host_url}api/webhook/{event_type}'
        resp = requests.post(url, json=payload, headers={
            'X-Webhook-Signature': hmac.new(
                WEBHOOK_SECRET.encode(),
                requests.Request('POST', url, json=payload).prepare().body or b'',
                hashlib.sha256
            ).hexdigest(),
            'X-Webhook-Source': 'webhook-simulator',
        }, timeout=5)
        return jsonify({'status': 'sent', 'response': resp.json()})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@webhook_bp.route('/api/webhook/logs')
def get_logs():
    logs = WebhookLog.query.order_by(WebhookLog.created_at.desc()).limit(50).all()
    return jsonify({'logs': [{
        'id': l.id,
        'event_type': l.event_type,
        'source': l.source,
        'payload': l.payload,
        'signature_valid': l.signature_valid,
        'processed': l.processed,
        'result': l.result,
        'created_at': l.created_at.isoformat(),
    } for l in logs]})
