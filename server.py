from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from typing import Dict, Any

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Разрешаем CORS для всех доменов (для продакшна лучше указать конкретные)

# Хранилище данных (в памяти) с аннотацией типа
data_store: Dict[str, Dict[str, Any]] = {}

@app.route('/')
def index():
    """Главная страница - отдаем статический index.html"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/data/<username>', methods=['GET'])
def get_data(username: str):
    """Получение данных пользователя"""
    user_data = data_store.get(username, {'inventory': [], 'shipments': []})
    return jsonify({
        'status': 'success',
        'data': user_data
    })

@app.route('/api/data/<username>', methods=['POST'])
def save_data(username: str):
    """Сохранение данных пользователя"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request must be JSON'}), 400
    
    try:
        new_data = request.get_json()
        data_store[username] = new_data
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    # Добавляем отключение debug в продакшн-режиме
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)