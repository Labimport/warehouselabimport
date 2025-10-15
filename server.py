import os
import json
import psycopg2
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

# === Настройки базы данных ===
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
BACKUP_FILE = "backup.json"


# === Модели ===
class Inventory(db.Model):
    id = db.Column(db.String, primary_key=True)
    user = db.Column(db.String)  # пользователь (админ)
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

    # --- Проверка наличия поля "user" ---
    try:
        with db.engine.connect() as conn:
            result = conn.execute("SELECT * FROM inventory LIMIT 1;")
    except Exception as e:
        if 'column "user" does not exist' in str(e) or "inventory.user" in str(e):
            print("⚙️ Добавляю недостающее поле 'user' в таблицу inventory...")
            with db.engine.connect() as conn:
                conn.execute('ALTER TABLE inventory ADD COLUMN "user" TEXT;')
                conn.commit()

    try:
        with db.engine.connect() as conn:
            result = conn.execute("SELECT * FROM shipment LIMIT 1;")
    except Exception as e:
        if 'column "user" does not exist' in str(e) or "shipment.user" in str(e):
            print("⚙️ Добавляю недостающее поле 'user' в таблицу shipment...")
            with db.engine.connect() as conn:
                conn.execute('ALTER TABLE shipment ADD COLUMN "user" TEXT;')
                conn.commit()

    print("✅ Таблицы успешно проверены или обновлены")


# === API ===
@app.route("/api/companies")
def get_companies():
    companies = sorted({i.company for i in Inventory.query.all()} | {"БТТ", "ЛИ"})
    return jsonify(list(companies))


@app.route("/api/data/<user>/<company>")
def get_data(user, company):
    inventory = Inventory.query.filter_by(company=company).all()
    shipments = Shipment.query.filter_by(company=company).all()
    return jsonify({
        "inventory": [i.__dict__ for i in inventory],
        "shipments": [s.__dict__ for s in shipments]
    })


@app.route("/api/data/<user>/<company>", methods=["POST"])
def save_data(user, company):
    data = request.get_json()
    inventory_data = data.get("inventory", [])
    shipment_data = data.get("shipments", [])

    Inventory.query.filter_by(company=company).delete()
    Shipment.query.filter_by(company=company).delete()

    for item in inventory_data:
        db.session.add(Inventory(**item))
    for item in shipment_data:
        db.session.add(Shipment(**item))

    db.session.commit()

    # --- Резервная копия ---
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


# === Раздача фронтенда ===
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(path):
        return send_from_directory(".", path)
    else:
        return send_from_directory(".", "index.html")


# === Точка входа ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
