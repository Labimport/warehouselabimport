from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# База данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warehouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---- МОДЕЛИ ----
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120))
    company = db.Column(db.String(120))
    date = db.Column(db.String(20))
    product = db.Column(db.String(120))
    lot = db.Column(db.String(120))
    quantity = db.Column(db.Float)
    expiryDate = db.Column(db.String(20))

class Shipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120))
    company = db.Column(db.String(120))
    date = db.Column(db.String(20))
    client = db.Column(db.String(120))
    product = db.Column(db.String(120))
    lot = db.Column(db.String(120))
    quantity = db.Column(db.Float)
    manager = db.Column(db.String(120))

with app.app_context():
    db.create_all()
    print("✅ Проверка структуры БД: всё в порядке")

# ---- РОУТЫ ----
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/companies')
def get_companies():
    companies = db.session.query(Inventory.company).distinct().all()
    result = sorted(set(c[0] for c in companies if c[0])) or ["БТТ", "ЛИ"]
    print("📊 Компании:", result)
    return jsonify(result)

@app.route('/api/data/<user>/<company>', methods=['GET'])
def get_data(user, company):
    inventory = Inventory.query.filter_by(user=user, company=company).all()
    shipments = Shipment.query.filter_by(user=user, company=company).all()
    return jsonify({
        "inventory": [vars(i) for i in inventory],
        "shipments": [vars(s) for s in shipments]
    })

@app.route('/api/data/<user>/<company>', methods=['POST'])
def save_data(user, company):
    data = request.json
    inventory = data.get('inventory', [])
    shipments = data.get('shipments', [])

    Inventory.query.filter_by(user=user, company=company).delete()
    Shipment.query.filter_by(user=user, company=company).delete()

    for i in inventory:
        db.session.add(Inventory(
            user=user, company=company, date=i.get("date"),
            product=i.get("product"), lot=i.get("lot"),
            quantity=i.get("quantity"), expiryDate=i.get("expiryDate")
        ))

    for s in shipments:
        db.session.add(Shipment(
            user=user, company=company, date=s.get("date"),
            client=s.get("client"), product=s.get("product"),
            lot=s.get("lot"), quantity=s.get("quantity"),
            manager=s.get("manager")
        ))

    db.session.commit()
    print(f"💾 Сохранение: {company}, {len(inventory)} остатков, {len(shipments)} отгрузок")
    return jsonify({"status": "ok"})

# ---- СИНХРОНИЗАЦИЯ ОТГРУЗОК ----
@app.route('/api/transfer', methods=['POST'])
def transfer_between_companies():
    data = request.json
    from_company = data.get("from")
    to_company = data.get("to")
    shipment = data.get("shipment")

    if not all([from_company, to_company, shipment]):
        return jsonify({"error": "Недостаточно данных"}), 400

    product = shipment.get("product")
    lot = shipment.get("lot")
    qty = float(shipment.get("quantity") or 0)
    date = shipment.get("date")
    expiry = shipment.get("expiryDate", "")
    user = shipment.get("user", "system")

    # 1️⃣ — Убавляем остаток у отправителя
    inv_from = Inventory.query.filter_by(company=from_company, product=product, lot=lot).first()
    if inv_from:
        inv_from.quantity = max(inv_from.quantity - qty, 0)
    else:
        db.session.add(Inventory(user=user, company=from_company, date=date, product=product, lot=lot, quantity=-qty, expiryDate=expiry))

    # 2️⃣ — Добавляем остаток у получателя
    inv_to = Inventory.query.filter_by(company=to_company, product=product, lot=lot).first()
    if inv_to:
        inv_to.quantity += qty
    else:
        db.session.add(Inventory(user=user, company=to_company, date=date, product=product, lot=lot, quantity=qty, expiryDate=expiry))

    db.session.commit()
    print(f"🔁 Передача {qty} шт {product} ({lot}) от {from_company} к {to_company}")
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
