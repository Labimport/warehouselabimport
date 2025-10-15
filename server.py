import os
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# === Настройки базы данных ===
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
print("✅ Таблицы созданы или уже существуют")

# === Получить список компаний ===
@app.route("/api/companies")
def get_companies():
    companies = sorted(list({i.company for i in Inventory.query.all()} | {"БТТ", "ЛИ"}))
    print(f"📊 Компании: {companies}")
    return jsonify(companies)

# === Получить все данные (инвентарь и отгрузки) ===
@app.route("/api/data/<user>/<company>", methods=["GET"])
def get_data(user, company):
    inventory = Inventory.query.filter_by(company=company).all()
    shipments = Shipment.query.filter_by(company=company).all()

    print(f"📦 Загружены данные {company}: {len(inventory)} остатков, {len(shipments)} отгрузок")

    # Автозаполнение
    products = sorted({i.product for i in inventory if i.product})
    lots_by_product = {p: sorted({i.lot for i in inventory if i.product == p and i.lot}) for p in products}
    clients = sorted({s.client for s in shipments if s.client})
    managers = sorted({s.manager for s in shipments if s.manager})

    return jsonify({
        "inventory": [
            {
                "id": i.id,
                "user": i.user,
                "company": i.company,
                "date": i.date,
                "product": i.product,
                "lot": i.lot,
                "quantity": i.quantity,
                "expiryDate": i.expiryDate
            } for i in inventory
        ],
        "shipments": [
            {
                "id": s.id,
                "user": s.user,
                "company": s.company,
                "date": s.date,
                "client": s.client,
                "product": s.product,
                "lot": s.lot,
                "quantity": s.quantity,
                "manager": s.manager
            } for s in shipments
        ],
        "autocomplete": {
            "products": products,
            "lots": lots_by_product,
            "clients": clients,
            "managers": managers
        }
    })

# === Сохранение данных ===
@app.route("/api/data/<user>/<company>", methods=["POST"])
def save_data(user, company):
    try:
        payload = request.json or {}
        inventory_data = payload.get("inventory", [])
        shipments_data = payload.get("shipments", [])

        print(f"💾 Сохранение: {company}, {len(inventory_data)} остатков, {len(shipments_data)} отгрузок")

        # --- Остатки ---
        for item in inventory_data:
            existing = Inventory.query.filter_by(id=item["id"]).first()
            if existing:
                existing.date = item["date"]
                existing.product = item["product"]
                existing.lot = item["lot"]
                existing.quantity = item["quantity"]
                existing.expiryDate = item.get("expiryDate")
                existing.user = user
                existing.company = company
            else:
                db.session.add(Inventory(
                    id=item["id"],
                    user=user,
                    company=company,
                    date=item["date"],
                    product=item["product"],
                    lot=item["lot"],
                    quantity=item["quantity"],
                    expiryDate=item.get("expiryDate")
                ))

        # --- Отгрузки ---
        for s in shipments_data:
            existing = Shipment.query.filter_by(id=s["id"]).first()
            if existing:
                existing.date = s["date"]
                existing.client = s["client"]
                existing.product = s["product"]
                existing.lot = s["lot"]
                existing.quantity = s["quantity"]
                existing.manager = s["manager"]
                existing.user = user
                existing.company = company
            else:
                db.session.add(Shipment(
                    id=s["id"],
                    user=user,
                    company=company,
                    date=s["date"],
                    client=s["client"],
                    product=s["product"],
                    lot=s["lot"],
                    quantity=s["quantity"],
                    manager=s["manager"]
                ))

        db.session.commit()
        print("✅ Данные сохранены успешно")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("❌ Ошибка при сохранении:", e)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# === Главная страница ===
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# === Статические файлы ===
@app.route("/<path:path>")
def static_files(path):
    static_dir = os.path.join(os.getcwd(), "static")
    if os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return "Not Found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
