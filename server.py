from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель данных с полем company
class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    company = db.Column(db.String(10), nullable=False)
    inventory = db.Column(db.JSON, nullable=False, default=[])
    shipments = db.Column(db.JSON, nullable=False, default=[])

    __table_args__ = (db.UniqueConstraint('username', 'company', name='uix_username_company'),)

# Создание таблиц
with app.app_context():
    db.create_all()

# Регистрация маршрута для главной страницы
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Эндпоинт для получения данных пользователя по компании
@app.route('/api/data/<username>/<company>', methods=['GET'])
def get_data(username, company):
    user_data = UserData.query.filter_by(username=username, company=company).first()
    if user_data:
        return jsonify({
            'inventory': user_data.inventory,
            'shipments': user_data.shipments
        })
    return jsonify({'inventory': [], 'shipments': []})

# Эндпоинт для сохранения данных пользователя по компании
@app.route('/api/data/<username>/<company>', methods=['POST'])
def save_data(username, company):
    user_data = UserData.query.filter_by(username=username, company=company).first()
    new_data = request.get_json()
    if user_data:
        user_data.inventory = new_data.get('inventory', [])
        user_data.shipments = new_data.get('shipments', [])
    else:
        user_data = UserData(username=username, company=company, inventory=new_data.get('inventory', []), shipments=new_data.get('shipments', []))
        db.session.add(user_data)
    db.session.commit()
    return jsonify({'status': 'success'})

# Эндпоинт для получения всех компаний (для просмотра без авторизации)
@app.route('/api/companies', methods=['GET'])
def get_companies():
    companies = db.session.query(UserData.company).distinct().all()
    return jsonify([c[0] for c in companies])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)