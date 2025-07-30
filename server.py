from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from typing import Dict, Any

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Для продакшна укажите конкретные домены в CORS(app, origins=[])

# Конфигурация базы данных
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'warehouse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class UserData(db.Model):
    __tablename__ = 'user_data'
    username = db.Column(db.String(80), primary_key=True)
    inventory = db.Column(db.JSON, nullable=False, default=list)  # list вместо []
    shipments = db.Column(db.JSON, nullable=False, default=list)

    def __repr__(self):
        return f'<UserData {self.username}>'

# Создание таблиц
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Главная страница"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/data/<username>', methods=['GET'])
def get_data(username: str):
    """Получение данных пользователя"""
    user_data = UserData.query.get(username)  # get() вместо filter_by().first()
    if user_data:
        return jsonify({
            'status': 'success',
            'data': {
                'inventory': user_data.inventory,
                'shipments': user_data.shipments
            }
        })
    return jsonify({
        'status': 'success',
        'data': {
            'inventory': [],
            'shipments': []
        }
    })

@app.route('/api/data/<username>', methods=['POST'])
def save_data(username: str):
    """Сохранение или обновление данных пользователя"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request must be JSON'}), 400

    try:
        new_data = request.get_json()
        user_data = UserData.query.get(username)
        
        if user_data:
            # Обновляем существующую запись
            user_data.inventory = new_data.get('inventory', user_data.inventory)
            user_data.shipments = new_data.get('shipments', user_data.shipments)
        else:
            # Создаем новую запись
            user_data = UserData(
                username=username,
                inventory=new_data.get('inventory', []),
                shipments=new_data.get('shipments', [])
            )
            db.session.add(user_data)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)