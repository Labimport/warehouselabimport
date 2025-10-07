import os
import urllib.parse
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import secrets
from typing import Dict, List, Any, Optional

# Настройка логирования с ротацией
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)

# Конфигурация приложения
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = None

def setup_database_url() -> str:
    """Настройка URL базы данных с обработкой Heroku Postgres"""
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Простая замена для Heroku
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    else:
        return 'postgresql://user:password@localhost:5432/warehouse'

Config.SQLALCHEMY_DATABASE_URI = setup_database_url()
app.config.from_object(Config)

CORS(app)
db = SQLAlchemy(app)

# Константы
VALID_COMPANIES = ['БТТ', 'ЛИ']
MAX_QUANTITY = 1000000  # Максимальное разумное количество

# Модели данных
class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.String(50), primary_key=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    product = db.Column(db.String(255), nullable=False)
    lot = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiryDate = db.Column(db.String(10))  # YYYY-MM-DD
    company = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    
    __table_args__ = (
        db.Index('idx_inventory_user_company', 'username', 'company'),
        db.Index('idx_inventory_product_lot', 'product', 'lot'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'date': self.date,
            'product': self.product,
            'lot': self.lot,
            'quantity': self.quantity,
            'expiryDate': self.expiryDate,
            'company': self.company
        }

class Shipment(db.Model):
    __tablename__ = 'shipments'
    
    id = db.Column(db.String(50), primary_key=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    product = db.Column(db.String(255), nullable=False)
    lot = db.Column(db.String(100), nullable=False)
    client = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    manager = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    
    __table_args__ = (
        db.Index('idx_shipments_user_company', 'username', 'company'),
        db.Index('idx_shipments_client', 'client'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'date': self.date,
            'product': self.product,
            'lot': self.lot,
            'client': self.client,
            'quantity': self.quantity,
            'manager': self.manager,
            'company': self.company
        }

# Валидаторы
def validate_company(company: str) -> bool:
    """Проверка валидности компании"""
    return company in VALID_COMPANIES

def validate_date(date_string: str) -> bool:
    """Проверка валидности даты в формате YYYY-MM-DD"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

def validate_quantity(quantity: Any) -> bool:
    """Проверка валидности количества"""
    try:
        qty = int(quantity)
        return 0 <= qty <= MAX_QUANTITY
    except (ValueError, TypeError):
        return False

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
    """Проверка наличия обязательных полей"""
    for field in required_fields:
        if not data.get(field):
            return f"Отсутствует обязательное поле: {field}"
    return None

def validate_inventory_item(item: Dict[str, Any]) -> Optional[str]:
    """Валидация элемента инвентаря"""
    # Проверка обязательных полей
    required_fields = ['id', 'date', 'product', 'lot', 'quantity']
    if error := validate_required_fields(item, required_fields):
        return error
    
    # Проверка даты
    if not validate_date(item['date']):
        return f"Неверный формат даты: {item['date']}"
    
    # Проверка количества
    if not validate_quantity(item['quantity']):
        return f"Неверное количество: {item['quantity']}"
    
    # Проверка даты годности (если указана)
    if item.get('expiryDate') and not validate_date(item['expiryDate']):
        return f"Неверный формат даты годности: {item['expiryDate']}"
    
    return None

def validate_shipment_item(item: Dict[str, Any]) -> Optional[str]:
    """Валидация элемента отгрузки"""
    # Проверка обязательных полей
    required_fields = ['id', 'date', 'product', 'lot', 'client', 'quantity', 'manager']
    if error := validate_required_fields(item, required_fields):
        return error
    
    # Проверка даты
    if not validate_date(item['date']):
        return f"Неверный формат даты: {item['date']}"
    
    # Проверка количества
    if not validate_quantity(item['quantity']):
        return f"Неверное количество: {item['quantity']}"
    
    return None

# Функция для инициализации таблиц
def init_db():
    """Инициализация базы данных"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Таблицы успешно созданы или уже существуют")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise

# Маршруты
@app.route('/')
def home():
    """Главная страница"""
    logger.info("Получен запрос на главную страницу")
    return jsonify({
        "status": "success",
        "message": "Warehouse API is running",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/health')
def health_check():
    """Проверка здоровья приложения"""
    try:
        # Простая проверка подключения к БД
        db.session.execute('SELECT 1')
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Получение списка компаний"""
    logger.info("Получен запрос GET /api/companies")
    return jsonify(VALID_COMPANIES)

@app.route('/api/data/<username>/<company>', methods=['GET'])
def get_data(username: str, company: str):
    """Получение данных пользователя для указанной компании"""
    logger.info(f"Получен запрос GET /api/data/{username}/{company}")
    
    # Валидация входных параметров
    if not username or not username.strip():
        return jsonify({'error': 'Неверное имя пользователя'}), 400
    
    if not validate_company(company):
        return jsonify({'error': f'Неверная компания. Допустимые значения: {", ".join(VALID_COMPANIES)}'}), 400

    try:
        # Получение данных из базы
        inventory = Inventory.query.filter_by(username=username, company=company).all()
        shipments = Shipment.query.filter_by(username=username, company=company).all()
        
        # Преобразование в словари
        data = {
            'inventory': [item.to_dict() for item in inventory],
            'shipments': [item.to_dict() for item in shipments]
        }
        
        logger.info(f"Успешно получены данные для {username}, {company}: "
                   f"{len(data['inventory'])} записей инвентаря, "
                   f"{len(data['shipments'])} записей отгрузок")
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных для {username}, {company}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/data/<username>/<company>', methods=['POST'])
def save_data(username: str, company: str):
    """Сохранение данных пользователя для указанной компании"""
    logger.info(f"Получен запрос POST /api/data/{username}/{company}")
    
    # Валидация входных параметров
    if not username or not username.strip():
        return jsonify({'error': 'Неверное имя пользователя'}), 400
    
    if not validate_company(company):
        return jsonify({'error': f'Неверная компания. Допустимые значения: {", ".join(VALID_COMPANIES)}'}), 400

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Отсутствуют данные'}), 400
        
        # Валидация данных инвентаря
        inventory_errors = []
        for i, item in enumerate(data.get('inventory', [])):
            if error := validate_inventory_item(item):
                inventory_errors.append(f"Инвентарь запись {i}: {error}")
        
        # Валидация данных отгрузок
        shipment_errors = []
        for i, item in enumerate(data.get('shipments', [])):
            if error := validate_shipment_item(item):
                shipment_errors.append(f"Отгрузка запись {i}: {error}")
        
        # Если есть ошибки валидации
        all_errors = inventory_errors + shipment_errors
        if all_errors:
            logger.warning(f"Ошибки валидации для {username}, {company}: {all_errors}")
            return jsonify({
                'error': 'Ошибки валидации данных',
                'details': all_errors
            }), 400
        
        # Начало транзакции
        db.session.begin_nested()
        
        try:
            # Удаление старых данных
            Inventory.query.filter_by(username=username, company=company).delete()
            Shipment.query.filter_by(username=username, company=company).delete()
            
            # Сохранение нового инвентаря
            for item in data.get('inventory', []):
                inv = Inventory(
                    id=item['id'],
                    date=item['date'],
                    product=item['product'],
                    lot=item['lot'],
                    quantity=item['quantity'],
                    expiryDate=item.get('expiryDate'),
                    company=company,
                    username=username
                )
                db.session.add(inv)
            
            # Сохранение новых отгрузок
            for item in data.get('shipments', []):
                ship = Shipment(
                    id=item['id'],
                    date=item['date'],
                    product=item['product'],
                    lot=item['lot'],
                    client=item['client'],
                    quantity=item['quantity'],
                    manager=item['manager'],
                    company=company,
                    username=username
                )
                db.session.add(ship)
            
            # Коммит транзакции
            db.session.commit()
            
            logger.info(f"Данные успешно сохранены для {username}, {company}: "
                       f"{len(data.get('inventory', []))} записей инвентаря, "
                       f"{len(data.get('shipments', []))} записей отгрузок")
            
            return jsonify({
                "message": "Данные успешно сохранены",
                "inventory_count": len(data.get('inventory', [])),
                "shipments_count": len(data.get('shipments', []))
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка транзакции при сохранении данных для {username}, {company}: {e}")
            return jsonify({'error': 'Ошибка сохранения данных в базу'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса для {username}, {company}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ресурс не найден'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Метод не разрешен'}), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    # Инициализация базы данных при запуске
    with app.app_context():
        init_db()
    
    # Запуск приложения
    app.run(host='0.0.0.0', port=10000, debug=False)