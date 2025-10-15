import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# === Настройки Flask ===
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# === Настройки базы данных ===
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL".lower())
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///warehouse.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# === Модели ===
class Inventory(db.Model):
    id = db.Column(db.String, primary_key=True)
    user = db.Column(db.String, nullable=True)
    company = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=True)
    product = db.Column(db.String, nullable=True)
    lot = db.Column(db.String, nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    expiryDate = db.Column(db.String, nullable=True)

class Shipment(db.Model):
    id = db.Column(db.String, primary_key=True)
    user = db.Column(db.String, nullable=True)
    company = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=True)
    client = db.Column(db.String, nullable=True)
    product = db.Column(db.String, nullable=True)
    lot = db.Column(db.String, nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    manager = db.Column(db.String, nullable=True)

# === Инициализация базы ===
with app.app_context():
    db.create_all()
    print("✅ Таблицы успешно созданы или уже существуют")

# === API ===

@app.route("/api/companies")
def get_companies():
    companies = sorted(set([i.company for i in Inventory.query.all()] +
                           [s.company for s in Shipment.query.all()] +
                           ["БТТ", "ЛИ"]))
    return jsonify(companies)

@app.route("/api/data/<user>/<company>", methods=["GET"])
def get_data(user, company):
    try:
        inventory = Inventory.query.filter_by(company=company).all()
        shipments = Shipment.query.filter_by(company=company).all()

        return jsonify({
            "inventory": [dict(
                id=i.id, user=i.user, company=i.company,
                date=i.date, product=i.product, lot=i.lot,
                quantity=i.quantity, expiryDate=i.expiryDate
            ) for i in inventory],
            "shipments": [dict(
                id=s.id, user=s.user, company=s.company,
                date=s.date, client=s.client, product=s.product,
                lot=s.lot, quantity=s.quantity, manager=s.manager
            ) for s in shipments]
        })
    except Exception as e:
        print("❌ Ошибка при получении данных:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/data/<user>/<company>", methods=["POST"])
def save_data(user, company):
    try:
        data = request.get_json()
        inv_data = data.get("inventory", [])
        shp_data = data.get("shipments", [])

        # Очистка старых данных этой компании
        Inventory.query.filter_by(company=company).delete()
        Shipment.query.filter_by(company=company).delete()

        # Добавляем новые данные
        for i in inv_data:
            db.session.add(Inventory(
                id=i.get("id"), user=user, company=company,
                date=i.get("date"), product=i.get("product"),
                lot=i.get("lot"), quantity=i.get("quantity"),
                expiryDate=i.get("expiryDate")
            ))

        for s in shp_data:
            db.session.add(Shipment(
                id=s.get("id"), user=user, company=company,
                date=s.get("date"), client=s.get("client"),
                product=s.get("product"), lot=s.get("lot"),
                quantity=s.get("quantity"), manager=s.get("manager")
            ))

        db.session.commit()
        print(f"✅ Данные сохранены для {company}")
        return jsonify({"status": "ok"})

    except Exception as e:
        db.session.rollback()
        print("❌ Ошибка при сохранении данных:", e)
        return jsonify({"error": str(e)}), 500


# === Обработка фронтенда (index.html) ===
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    folder = os.path.join(os.getcwd(), "static")
    full_path = os.path.join(folder, path)

    if path != "" and os.path.exists(full_path):
        return send_from_directory(folder, path)
    return send_from_directory(folder, "index.html")


# === Точка входа ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
