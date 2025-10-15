from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import json

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# === Настройка подключения к PostgreSQL ===
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://warehouse_db_new_user:My65iK0GpKzjmzgCtENhXngWUwRZaCOI@dpg-d3iejrbipnbc73e4gc1g-a/warehouse_db_new"
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
BACKUP_FILE = "backup.json"

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

# === Инициализация базы ===
with app.app_context():
    db.create_all()
    print("✅ Таблицы успешно созданы или уже существуют")

    # === Восстановление из backup.json при пустой базе ===
    if not Inventory.query.first() and os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for i in data.get("inventory", []):
                    db.session.add(Inventory(**i))
                for s in data.get("shipments", []):
                    db.session.add(Shipment(**s))
                db.session.commit()
                print("♻️ Данные восстановлены из backup.json")
            except Exception as e:
                print(f"⚠️ Ошибка восстановления из backup.json: {e}")

# === Главная страница ===
@app.route("/")
def index():
    print("Получен запрос на главную страницу")
    return send_from_directory(".", "index.html")

# === API: получить список компаний ===
@app.route("/api/companies")
def get_companies():
    companies = db.session.query(Inventory.company).distinct().all()
    companies = [c[0] for c in companies if c[0]] or ["БТТ", "ЛИ"]
    print(f"📊 Возвращены компании: {companies}")
    return jsonify(companies)

# === API: получить данные пользователя ===
@app.route("/api/data/<user>/<company>")
def get_data(user, company):
    print(f"📥 Получен запрос GET /api/data/{user}/{company}")
    try:
        inv = Inventory.query.filter(Inventory.user == user, Inventory.company == company).all()
        shp = Shipment.query.filter(Shipment.user == user, Shipment.company == company).all()

        inventory = [dict(
            id=i.id,
            date=i.date,
            product=i.product,
            lot=i.lot,
            quantity=i.quantity,
            expiryDate=i.expiryDate,
            company=i.company
        ) for i in inv]

        shipments = [dict(
            id=s.id,
            date=s.date,
            client=s.client,
            product=s.product,
            lot=s.lot,
            quantity=s.quantity,
            manager=s.manager,
            company=s.company
        ) for s in shp]

        print(f"✅ Найдены данные для {user}, {company}: {len(inventory)} остатков, {len(shipments)} отгрузок")
        return jsonify({"inventory": inventory, "shipments": shipments})
    except Exception as e:
        print(f"❌ Ошибка при получении данных: {e}")
        return jsonify({"inventory": [], "shipments": []})

# === API: сохранить данные пользователя ===
@app.route("/api/data/<user>/<company>", methods=["POST"])
def save_data(user, company):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Пустые данные"}), 400

        # Удаляем старые записи только для этой компании и пользователя
        Inventory.query.filter(Inventory.user == user, Inventory.company == company).delete()
        Shipment.query.filter(Shipment.user == user, Shipment.company == company).delete()

        for i in data.get("inventory", []):
            db.session.add(Inventory(
                id=i["id"],
                user=user,
                company=i.get("company", company),
                date=i.get("date"),
                product=i.get("product"),
                lot=i.get("lot"),
                quantity=float(i.get("quantity", 0)),
                expiryDate=i.get("expiryDate", "")
            ))

        for s in data.get("shipments", []):
            db.session.add(Shipment(
                id=s["id"],
                user=user,
                company=s.get("company", company),
                date=s.get("date"),
                client=s.get("client"),
                product=s.get("product"),
                lot=s.get("lot"),
                quantity=float(s.get("quantity", 0)),
                manager=s.get("manager")
            ))

        db.session.commit()
        print(f"💾 Данные сохранены для {user}, {company}")

        # === Сохраняем бэкап в JSON ===
        all_inventory = [i.__dict__ for i in Inventory.query.all()]
        all_shipments = [s.__dict__ for s in Shipment.query.all()]
        for obj_list in (all_inventory, all_shipments):
            for obj in obj_list:
                obj.pop("_sa_instance_state", None)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump({"inventory": all_inventory, "shipments": all_shipments}, f, ensure_ascii=False, indent=2)
        print("💾 Резервная копия сохранена в backup.json")

        return jsonify({"status": "ok"})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка сохранения: {e}")
        return jsonify({"error": str(e)}), 500

# === Тестовые данные (на всякий случай) ===
@app.route("/api/init_test_data")
def init_test_data():
    if Inventory.query.first() or Shipment.query.first():
        return jsonify({"status": "exists"})

    sample_data = {
        "inventory": [
            {"id": "inv_1", "user": "Леонид", "company": "БТТ", "date": "2025-10-12", "product": "YRM 1009 Dexamethasone", "lot": "2412A168708C", "quantity": 10, "expiryDate": "2026-06-05"},
            {"id": "inv_2", "user": "Леонид", "company": "ЛИ", "date": "2025-10-12", "product": "Lunavi Ultraswab ATP", "lot": "20250818", "quantity": 5, "expiryDate": "2026-06-06"}
        ],
        "shipments": [
            {"id": "ship_1", "user": "Леонид", "company": "БТТ", "date": "2025-10-13", "client": "Медистра", "product": "YRM 1009 Dexamethasone", "lot": "2412A168708C", "quantity": 2, "manager": "Ольга"},
            {"id": "ship_2", "user": "Леонид", "company": "ЛИ", "date": "2025-10-13", "client": "Слуцкий сыродельный", "product": "Lunavi Ultraswab ATP", "lot": "20250818", "quantity": 1, "manager": "Леонид"}
        ]
    }

    for i in sample_data["inventory"]:
        db.session.add(Inventory(**i))
    for s in sample_data["shipments"]:
        db.session.add(Shipment(**s))
    db.session.commit()

    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print("✅ Тестовые данные добавлены и сохранены в backup.json")
    return jsonify({"status": "created"})

# === Запуск ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
