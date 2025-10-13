from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ==========================
# 📦 Настройка базы данных
# ==========================
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    print("⚠️ DATABASE_URL не найден, используется локальный SQLite")
    db_url = "sqlite:///data.db"

# Исправляем URL для PostgreSQL (Render иногда передаёт старый формат)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================
# 🧱 Модель таблицы
# ==========================
class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    company = db.Column(db.String(80), nullable=False)
    inventory = db.Column(db.JSON, nullable=False, default=[])
    shipments = db.Column(db.JSON, nullable=False, default=[])

    __table_args__ = (
        db.UniqueConstraint("username", "company", name="uix_username_company"),
    )

# ==========================
# 🚀 Инициализация данных
# ==========================
with app.app_context():
    db.create_all()
    print("✅ Таблицы успешно созданы или уже существуют")

    # Проверяем, есть ли данные
    existing_btt = UserData.query.filter_by(username="Леонид", company="БТТ").first()
    existing_li = UserData.query.filter_by(username="Леонид", company="ЛИ").first()

    # Если нет — добавляем стартовые записи
    if not existing_btt:
        db.session.add(UserData(
            username="Леонид",
            company="БТТ",
            inventory=[{
                "date": "2025-10-01",
                "product": "Продукт1",
                "lot": "A1",
                "quantity": 100,
                "expiryDate": "2026-10-01"
            }],
            shipments=[{
                "date": "2025-10-02",
                "product": "Продукт1",
                "lot": "A1",
                "client": "Клиент1",
                "quantity": 50,
                "manager": "Менеджер1"
            }]
        ))
        print("🟢 Добавлены тестовые данные для компании БТТ")

    if not existing_li:
        db.session.add(UserData(
            username="Леонид",
            company="ЛИ",
            inventory=[{
                "date": "2025-10-01",
                "product": "Продукт2",
                "lot": "B1",
                "quantity": 200,
                "expiryDate": "2026-10-01"
            }],
            shipments=[{
                "date": "2025-10-02",
                "product": "Продукт2",
                "lot": "B1",
                "client": "Клиент2",
                "quantity": 100,
                "manager": "Менеджер2"
            }]
        ))
        print("🟢 Добавлены тестовые данные для компании ЛИ")

    db.session.commit()
    print("✅ Инициализация данных завершена")

# ==========================
# 🌐 Маршруты API
# ==========================
@app.route("/")
def serve_index():
    print("📄 Отправка index.html")
    return send_from_directory(".", "index.html")

@app.route("/api/companies", methods=["GET"])
def get_companies():
    print("📊 Запрос компаний")
    companies = db.session.query(UserData.company).distinct().all()
    return jsonify([c[0] for c in companies])

@app.route("/api/data/<username>/<company>", methods=["GET"])
def get_data(username, company):
    print(f"📥 Запрос данных: {username} / {company}")
    user_data = UserData.query.filter_by(username=username, company=company).first()
    if user_data:
        return jsonify({
            "inventory": user_data.inventory,
            "shipments": user_data.shipments
        })
    return jsonify({"inventory": [], "shipments": []})

@app.route("/api/data/<username>/<company>", methods=["POST"])
def save_data(username, company):
    print(f"📤 Сохранение данных: {username} / {company}")
    data = request.get_json()
    if not data:
        return jsonify({"error": "Нет данных"}), 400

    user_data = UserData.query.filter_by(username=username, company=company).first()
    if user_data:
        user_data.inventory = data.get("inventory", [])
        user_data.shipments = data.get("shipments", [])
    else:
        user_data = UserData(
            username=username,
            company=company,
            inventory=data.get("inventory", []),
            shipments=data.get("shipments", [])
        )
        db.session.add(user_data)
    db.session.commit()
    return jsonify({"status": "success"})

# ==========================
# 🏁 Точка запуска
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
