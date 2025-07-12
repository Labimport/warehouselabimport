from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Хранилище данных (в памяти)
data_store = {}

# Эндпоинт для получения данных пользователя
@app.route('/api/data/<username>', methods=['GET'])
def get_data(username):
    user_data = data_store.get(username, {'inventory': [], 'shipments': []})
    return jsonify(user_data)

# Эндпоинт для сохранения данных пользователя
@app.route('/api/data/<username>', methods=['POST'])
def save_data(username):
    global data_store
    new_data = request.get_json()
    data_store[username] = new_data
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)