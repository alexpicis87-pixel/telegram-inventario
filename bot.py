import sqlite3
import os
from flask import Flask, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading

# ==============================
# Configuración
# ==============================
BOT_TOKEN = "6436352209:AAHH8IWy246pACneF3NPFhdJcsjkokmfOlU"
DB_FILE = "inventario.db"
APP_URL = os.environ.get("APP_URL", "https://tu-app.onrender.com")  # Cambia por tu URL de Render

# ==============================
# Base de datos SQLite
# ==============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            producto TEXT PRIMARY KEY,
            stock INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            cantidad INTEGER,
            accion TEXT,
            persona TEXT,
            telegram_user TEXT,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

def agregar_producto(producto, cantidad, persona, telegram_user, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT stock FROM inventario WHERE producto=?", (producto,))
    row = c.fetchone()
    if row:
        nuevo_stock = row[0] + cantidad
        c.execute("UPDATE inventario SET stock=? WHERE producto=?", (nuevo_stock, producto))
    else:
        nuevo_stock = cantidad
        c.execute("INSERT INTO inventario (producto, stock) VALUES (?, ?)", (producto, cantidad))

    c.execute("""
        INSERT INTO movimientos (producto, cantidad, accion, persona, telegram_user, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (producto, cantidad, "agregar", persona, telegram_user, user_id))

    conn.commit()
    conn.close()
    return nuevo_stock

def vender_producto(producto, cantidad, persona, telegram_user, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT stock FROM inventario WHERE producto=?", (producto,))
    row = c.fetchone()
    if not row or row[0] < cantidad:
        conn.close()
        return None

    nuevo_stock = row[0] - cantidad
    c.execute("UPDATE inventario SET stock=? WHERE producto=?", (nuevo_stock, producto))

    c.execute("""
        INSERT INTO movimientos (producto, cantidad, accion, persona, telegram_user, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (producto, cantidad, "vender", persona, telegram_user, user_id))

    conn.commit()
    conn.close()
    return nuevo_stock

def obtener_inventario():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT producto, stock FROM inventario")
    datos = c.fetchall()
    conn.close()
    return datos

# ==============================
# BOT Telegram
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bienvenido al Bot de Inventario.\nUsa /agregar, /vender, /inventario")

async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        cantidad = int(context.args[1])
        persona_input = " ".join(context.args[2:]) if len(context.args) > 2 else ""

        user = update.effective_user
        persona_telegram = user.username if user.username else user.first_name
        persona = persona_input if persona_input else persona_telegram

        nuevo_stock = agregar_producto(producto, cantidad, persona, persona_telegram, user.id)
        await update.message.reply_text(f"✅ {cantidad} {producto} agregado.\n📦 Stock actual: {nuevo_stock}")
    except:
        await update.message.reply_text("❌ Uso correcto: /agregar producto cantidad persona")

async def vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        cantidad = int(context.args[1])
        persona_input = " ".join(context.args[2:]) if len(context.args) > 2 else ""

        user = update.effective_user
        persona_telegram = user.username if user.username else user.first_name
        persona = persona_input if persona_input else persona_telegram

        nuevo_stock = vender_producto(producto, cantidad, persona, persona_telegram, user.id)
        if nuevo_stock is None:
            await update.message.reply_text("⚠️ No hay suficiente stock o el producto no existe.")
            return

        await update.message.reply_text(f"💸 {cantidad} {producto} vendido.\n📦 Stock actual: {nuevo_stock}")
    except:
        await update.message.reply_text("❌ Uso correcto: /vender producto cantidad persona")

async def inventario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🌐 Consulta el inventario aquí: {APP_URL}")

# ==============================
# Servidor Flask para ver inventario en HTML
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    datos = obtener_inventario()
    html = """
    <h1>📦 Inventario Actual</h1>
    <table border="1" cellpadding="5">
      <tr><th>Producto</th><th>Stock</th></tr>
      {% for p, s in datos %}
      <tr><td>{{p}}</td><td>{{s}}</td></tr>
      {% endfor %}
    </table>
    """
    return render_template_string(html, datos=datos)

# ==============================
# Main
# ==============================
def main():
    init_db()

    # Iniciar BOT en un hilo aparte
    def run_bot():
        app_tg = Application.builder().token(BOT_TOKEN).build()
        app_tg.add_handler(CommandHandler("start", start))
        app_tg.add_handler(CommandHandler("agregar", agregar))
        app_tg.add_handler(CommandHandler("vender", vender))
        app_tg.add_handler(CommandHandler("inventario", inventario_cmd))
        print("🤖 Bot de inventario en marcha...")
        app_tg.run_polling()

    threading.Thread(target=run_bot).start()

    # Iniciar servidor Flask
    print("🌐 Servidor web corriendo en Render")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    main()
