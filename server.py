from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:5432/warehouse'
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

class Shipment(db.Model):
    id = db.Column(db.String, primary_key=True)
    date = db.Column(db.String)
    product = db.Column(db.String)
    lot = db.Column(db.String)
    client = db.Column(db.String)
    quantity = db.Column(db.Integer)
    manager = db.Column(db.String)
    company = db.Column(db.String)

# Создание таблиц
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    print("Получен запрос на главную страницу")
    return "", 200

@app.route('/api/companies', methods=['GET'])
def get_companies():
    print("Получен запрос GET /api/companies")
    return jsonify(['БТТ', 'ЛИ'])

@app.route('/api/data/<username>/<company>', methods=['GET'])
def get_data(username, company):
    print(f"Получен запрос GET /api/data/{username}/{company}")
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
    print(f"Найдены данные для {username}, {company}: {data['inventory']}, {data['shipments']}")
    return jsonify(data)

@app.route('/api/data/<username>/<company>', methods=['POST'])
def save_data(username, company):
    print(f"Получен запрос POST /api/data/{username}/{company}")
    data = request.get_json()
    # Очистка существующих данных для этой компании
    Inventory.query.filter_by(username=username, company=company).delete()
    Shipment.query.filter_by(username=username, company=company).delete()
    # Сохранение новых данных
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
    print(f"Данные успешно сохранены для {username}, {company}")
    return jsonify({"message": "Данные сохранены"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)