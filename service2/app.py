"""Second backend service - runs on port 8002. Simulates a user profile microservice."""
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


USERS = {
    '1': {'id': 1, 'username': 'alice', 'nickname': 'Alice', 'badges': ['verified', 'premium'], 'join_date': '2025-01-15'},
    '2': {'id': 2, 'username': 'bob', 'nickname': 'Bob', 'badges': ['contributor'], 'join_date': '2025-03-22'},
    '3': {'id': 3, 'username': 'charlie', 'nickname': 'Charlie', 'badges': ['verified', 'moderator'], 'join_date': '2024-11-08'},
}


ORDERS = {
    '1': [{'id': 101, 'product': 'Premium Membership', 'price': 29.9, 'status': 'active'}, {'id': 102, 'product': '1000 Coins Pack', 'price': 9.9, 'status': 'completed'}],
    '2': [{'id': 201, 'product': '500 Coins Pack', 'price': 4.9, 'status': 'completed'}],
    '3': [{'id': 301, 'product': 'Premium Membership', 'price': 29.9, 'status': 'expired'}, {'id': 302, 'product': 'Creator Badge', 'price': 14.9, 'status': 'active'}],
}


@app.route('/api/v2/user/<user_id>')
def get_user(user_id):
    """User profile data - service 2"""
    user = USERS.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'service': 'user-profile-service', 'port': 8002, 'data': user})


@app.route('/api/v2/user/<user_id>/orders')
def get_user_orders(user_id):
    """User order history - service 2"""
    user = USERS.get(user_id)
    orders = ORDERS.get(user_id, [])
    return jsonify({'service': 'order-service', 'port': 8002, 'data': {'user': user, 'orders': orders}})


@app.route('/api/v2/stats')
def get_stats():
    """Platform statistics - service 2"""
    return jsonify({
        'service': 'stats-service',
        'port': 8002,
        'data': {
            'total_users': len(USERS),
            'total_orders': sum(len(o) for o in ORDERS.values()),
            'active_premium': sum(1 for orders in ORDERS.values() for o in orders if o['product'] == 'Premium Membership' and o['status'] == 'active'),
        }
    })


if __name__ == '__main__':
    print('Service 2 starting on port 8002...')
    app.run(host='127.0.0.1', port=8002, debug=False)
