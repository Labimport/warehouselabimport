import os
import urllib.parse
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Извлечение DATABASE_URL и настройка для SQLAlchemy
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    result = urllib.parse.urlparse(db_url)
    username = result.username
    password = result.password
    db_url = f"postgresql://{username}:{password}@{result.hostname}:{result.port}/{result.path[1:]}?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'postgresql://user:password@localhost:5432/warehouse'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db = SQLAlchemy(app)

# Модели
class Inventory(db.Model):
    id = db.Column(db.String, primary_key=True)
    date = db.Column(db.String)
    product = db.Column(db.String)
    lot = db.Column(db.String)
    quantity = db.Column(db.Integer)
    expiryDate = db.Column(db.String)
    company = db.Column(db.String)
    username = db.Column(db.String)

class Shipment(db.Model):
    id = db.Column(db.String, primary_key=True)
    date = db.Column(db.String)
    product = db.Column(db.String)
    lot = db.Column(db.String)
    client = db.Column(db.String)
    quantity = db.Column(db.Integer)
    manager = db.Column(db.String)
    company = db.Column(db.String)
    username = db.Column(db.String)

# Функция для инициализации таблиц (вызывается вручную при необходимости)
def init_db():
    try:
        with app.app_context():
            db.create_all()
            logger.info("Таблицы успешно созданы или уже существуют")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")

# Инициализация при старте (без принудительного создания таблиц)
# init_db()  # Комментируем для теста, чтобы избежать конфликтов

@app.route('/')
def home():
    logger.info("Получен запрос на главную страницу")
    return "", 200

@app.route('/api/companies', methods=['GET'])
def get_companies():
    logger.info("Получен запрос GET /api/companies")
    return jsonify(['БТТ', 'ЛИ'])

@app.route('/api/data/<username>/<company>', methods=['GET'])
def get_data(username, company):
    logger.info(f"Получен запрос GET /api/data/{username}/{company}")
    try:
        inventory = Inventory.query.filter_by(username=username, company=company).all()
        shipments = Shipment.query.filter_by(username=username, company=company).all()
        data = {
            'inventory': [{'id': i.id, 'date': i.date, 'product': i.product, 'lot': i.lot, 
                          'quantity': i.quantity, 'expiryDate': i.expiryDate, 'company': i.company} 
                          for i in inventory],
            'shipments': [{'id': s.id, 'date': s.date, 'product': s.product, 'lot': s.lot, 
                          'client': s.client, 'quantity': s.quantity, 'manager': s.manager, 
                          'company': s.company} for s in shipments]
        }
        logger.info(f"Найдены данные для {username}, {company}: {data['inventory']}, {data['shipments']}")
        return jsonify(data)
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/data/<username>/<company>', methods=['POST'])
def save_data(username, company):
    logger.info(f"Получен запрос POST /api/data/{username}/{company}")
    try:
        data = request.get_json()
        Inventory.query.filter_by(username=username, company=company).delete()
        Shipment.query.filter_by(username=username, company=company).delete()
        for item in data.get('inventory', []):
            inv = Inventory(id=item['id'], date=item['date'], product=item['product'], 
                           lot=item['lot'], quantity=item['quantity'], expiryDate=item['expiryDate'], 
                           company=company, username=username)
            db.session.add(inv)
        for item in data.get('shipments', []):
            ship = Shipment(id=item['id'], date=item['date'], product=item['product'], 
                           lot=item['lot'], client=item['client'], quantity=item['quantity'], 
                           manager=item['manager'], company=company, username=username)
            db.session.add(ship)
        db.session.commit()
        logger.info(f"Данные успешно сохранены для {username}, {company}")
        return jsonify({"message": "Данные сохранены"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при сохранении данных: {e}")
        return jsonify({'error': 'Ошибка сохранения данных'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)