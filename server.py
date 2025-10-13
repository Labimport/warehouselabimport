from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# ==============================
# 📦 Настройка базы данных
# ==============================
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("⚠️ DATABASE_URL не настроен, используется SQLite на диске (data.db)")
    db_url = 'sqlite:///data.db'

# Render требует SSL для PostgreSQL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==============================
# 📋 Модель данных
# ==============================
class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    company = db.Column(db.String(10), nullable=False)
    inventory = db.Column(db.JSON, nullable=False, default=[])
    shipments = db.Column(db.JSON, nullable=False, default=[])
    __table_args__ = (db.UniqueConstraint('username', 'company', name='uix_username_company'),)

# ==============================
# 🧱 Инициализация таблиц и данных
# ==============================
try:
    with app.app_context():
        db.create_all()
        print("✅ Таблицы успешно созданы или уже существуют")

        existing_btt = UserData.query.filter_by(username='Леонид', company='БТТ').first()
        existing_li = UserData.query.filter_by(username='Леонид', company='ЛИ').first()

        if not existing_btt:
            print("Добавляю тестовые данные для компании БТТ...")
            db.session.add(UserData(
                username='Леонид',
                company='БТТ',
                inventory=[{'date': '2025-10-01', 'product': 'Продукт1', 'lot': 'A1', 'quantity': 100, 'expiryDate': '2026-10-01'}],
                shipments=[{'date': '2025-10-02', 'product': 'Продукт1', 'lot': 'A1', 'client': 'Клиент1', 'quantity': 50, 'manager': 'Менеджер1'}]
            ))

        if not existing_li:
            print("Добавляю тестовые данные для компании ЛИ...")
            db.session.add(UserData(
                username='Леонид',
                company='ЛИ',
                inventory=[{'date': '2025-10-01', 'product': 'Продукт2', 'lot': 'B1', 'quantity': 200, 'expiryDate': '2026-10-01'}],
                shipments=[{'date': '2025-10-02', 'product': 'Продукт2', 'lot': 'B1', 'client': 'Клиент2', 'quantity': 100, 'manager': 'Менеджер2'}]
            ))

        db.session.commit()
        print("✅ Тестовые данные добавлены (если их не было)")
except Exception as e:
    print(f"❌ Ошибка при создании таблиц или добавлении данных: {e}")

# ==============================
# 🌐 Маршруты API
# ==============================

@app.route('/')
def index():
    print("Получен запрос на главную страницу")
    return app.send_static_file('index.html')

@app.route('/api/data/<username>/<company>', methods=['GET'])
def get_data(username, company):
    print(f"📥 Получен запрос GET /api/data/{username}/{company}")
    try:
        user_data = UserData.query.filter_by(username=username, company=company).first()
        if user_data:
            print(f"✅ Найдены данные для {username}, {company}")
            return jsonify({
                'inventory': user_data.inventory or [],
                'shipments': user_data.shipments or []
            })
        print(f"⚠️ Нет данных для {username}, {company}, возвращаю пустой JSON")
        return jsonify({'inventory': [], 'shipments': []})
    except Exception as e:
        print(f"❌ Ошибка обработки запроса: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/<username>/<company>', methods=['POST'])
def save_data(username, company):
    print(f"📤 Получен запрос POST /api/data/{username}/{company}")
    try:
        user_data = UserData.query.filter_by(username=username, company=company).first()
        new_data = request.get_json() or {}
        if user_data:
            user_data.inventory = new_data.get('inventory', [])
            user_data.shipments = new_data.get('shipments', [])
        else:
            user_data = UserData(username=username, company=company,
                                 inventory=new_data.get('inventory', []),
                                 shipments=new_data.get('shipments', []))
            db.session.add(user_data)
        db.session.commit()
        print(f"✅ Данные успешно сохранены для {username}, {company}")
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    print("📊 Получен запрос GET /api/companies")
    try:
        companies = db.session.query(UserData.company).distinct().all()
        result = [c[0] for c in companies]
        print(f"✅ Возвращены компании: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Ошибка получения списка компаний: {e}")
        return jsonify([])

# ==============================
# 🚀 Запуск приложения
# ==============================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
