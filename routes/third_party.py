import requests
from flask import Blueprint, request, jsonify, current_app

third_bp = Blueprint('third_party', __name__, url_prefix='/api/third')


@third_bp.route('/weather')
def weather():
    city = request.args.get('city', 'Beijing')
    api_key = current_app.config.get('WEATHER_API_KEY', '')

    if not api_key:
        return jsonify({'error': 'Weather API key not configured'}), 500

    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        resp = requests.get(url, params={
            'q': city,
            'appid': api_key,
            'units': 'metric',
            'lang': 'zh_cn',
        }, timeout=10)

        if resp.status_code != 200:
            return jsonify({'error': 'City not found or API error'}), 404

        data = resp.json()
        return jsonify({
            'city': data['name'],
            'country': data.get('sys', {}).get('country', ''),
            'temp': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'description': data['weather'][0]['description'],
            'wind_speed': data['wind']['speed'],
            'icon': data['weather'][0]['icon'],
        })
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500
