import os
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
CORS(app)

# === Подключение к БД ===
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///warehouse.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# === Модели ===
class Inventory(db.Model):
    id = db.Column(db.String, primary_key=True)
    user = db.Column(db.String)
    company = db.Column(db.String)
    date = db.Column(db.String)
    product = db.Column(db.String)
    lot = db.Column(db.String)
    quantity = db.Column(db.Float)
    expiryDate = db.Column(db.String)

class Shipment(db.Model):
    id = db.Column(db.String, primary_key=True)
    user = db.Column(db.String)
    company = db.Column(db.String)
    date = db.Column(db.String)
    client = db.Column(db.String)
    product = db.Column(db.String)
    lot = db.Column(db.String)
    quantity = db.Column(db.Float)
    manager = db.Column(db.String)

# === Создание таблиц ===
with app.app_context():
    db.create_all()
print("✅ Таблицы успешно созданы или уже существуют")

# === Список компаний ===
@app.route("/api/companies")
def get_companies():
    companies = sorted(list({i.company for i in Inventory.query.all()} | {"БТТ", "ЛИ"}))
    print(f"📊 Возвращены компании: {companies}")
    return jsonify(companies)

# === Получение данных по пользователю и компании ===
@app.route("/api/data/<user>/<company>", methods=["GET"])
def get_data(user, company):
    try:
        inventory = Inventory.query.filter_by(company=company).all()
        shipments = Shipment.query.filter_by(company=company).all()

        return jsonify({
            "inventory": [
                {
                    "id": i.id,
                    "company": i.company,
                    "user": i.user,
                    "date": i.date,
                    "product": i.product,
                    "lot": i.lot,
                    "quantity": i.quantity,
                    "expiryDate": i.expiryDate
                }
                for i in inventory
            ],
            "shipments": [
                {
                    "id": s.id,
                    "company": s.company,
                    "user": s.user,
                    "date": s.date,
                    "client": s.client,
                    "product": s.product,
                    "lot": s.lot,
                    "quantity": s.quantity,
                    "manager": s.manager
                }
                for s in shipments
            ]
        })
    except OperationalError as e:
        print("❌ Ошибка при загрузке данных:", e)
        return jsonify({"inventory": [], "shipments": []}), 500

# === Сохранение данных (обновление и добавление без очистки) ===
@app.route("/api/data/<user>/<company>", methods=["POST"])
def save_data(user, company):
    try:
        data = request.json
        inventory_data = data.get("inventory", [])
        shipment_data = data.get("shipments", [])

        print(f"📥 Сохранение данных для {company}: {len(inventory_data)} остатков, {len(shipment_data)} отгрузок")

        # --- Сохранение остатков ---
        for item in inventory_data:
            db_item = Inventory.query.filter_by(id=item.get("id")).first()
            if db_item:
                db_item.user = user
                db_item.company = company
                db_item.date = item.get("date")
                db_item.product = item.get("product")
                db_item.lot = item.get("lot")
                db_item.quantity = item.get("quantity")
                db_item.expiryDate = item.get("expiryDate")
            else:
                db.session.add(Inventory(
                    id=item.get("id"),
                    user=user,
                    company=company,
                    date=item.get("date"),
                    product=item.get("product"),
                    lot=item.get("lot"),
                    quantity=item.get("quantity"),
                    expiryDate=item.get("expiryDate")
                ))

        # --- Сохранение отгрузок ---
        for item in shipment_data:
            db_item = Shipment.query.filter_by(id=item.get("id")).first()
            if db_item:
                db_item.user = user
                db_item.company = company
                db_item.date = item.get("date")
                db_item.client = item.get("client")
                db_item.product = item.get("product")
                db_item.lot = item.get("lot")
                db_item.quantity = item.get("quantity")
                db_item.manager = item.get("manager")
            else:
                db.session.add(Shipment(
                    id=item.get("id"),
                    user=user,
                    company=company,
                    date=item.get("date"),
                    client=item.get("client"),
                    product=item.get("product"),
                    lot=item.get("lot"),
                    quantity=item.get("quantity"),
                    manager=item.get("manager")
                ))

        db.session.commit()
        print("✅ Данные успешно сохранены.")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("❌ Ошибка при сохранении:", e)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# === Главная страница (index.html) ===
@app.route("/")
def index():
    print("📄 Получен запрос на главную страницу")
    return send_from_directory("static", "index.html")

# === Обслуживание статических файлов ===
@app.route("/<path:path>")
def static_files(path):
    static_dir = os.path.join(os.getcwd(), "static")
    if os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return "Not Found", 404

# === Запуск сервера ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
