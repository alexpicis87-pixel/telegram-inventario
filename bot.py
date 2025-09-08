import json
import os
import threading
import asyncio
from flask import Flask, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = "6436352209:AAHH8IWy246pACneF3NPFhdJcsjkokmfOlU"
APP_URL = "https://telegram-inventario-mq1c.onrender.com"  # Render URL
DATA_FILE = "inventario.json"
AUTHORIZED_USERS = [1886047632]  # Agrega más IDs aquí

# ---------------- DATA ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

with open(DATA_FILE, "r") as f:
    try:
        inventario = json.load(f)
    except json.JSONDecodeError:
        inventario = {}

def guardar_inventario():
    with open(DATA_FILE, "w") as f:
        json.dump(inventario, f, indent=4)

# ---------------- PERMISOS ----------------
def autorizado(update: Update) -> bool:
    """Verifica si el usuario está autorizado"""
    return update.effective_user.id in AUTHORIZED_USERS

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await update.message.reply_text("❌ No estás autorizado para usar este bot.")
        return
    await update.message.reply_text("🤖 Bienvenido al Bot de Inventario!\nUsa /agregar, /vender o /inventario.")

async def miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el ID del usuario"""
    await update.message.reply_text(f"🆔 Tu ID es: {update.effective_user.id}")

async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await update.message.reply_text("❌ No estás autorizado para usar este bot.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /agregar <producto> <cantidad>")
        return
    producto = context.args[0].lower()
    cantidad = int(context.args[1])
    usuario = update.effective_user.username or update.effective_user.first_name

    if producto not in inventario:
        inventario[producto] = {"cantidad": 0, "ultima_accion": ""}

    inventario[producto]["cantidad"] += cantidad
    inventario[producto]["ultima_accion"] = f"Añadido por {usuario}"

    guardar_inventario()
    await update.message.reply_text(f"✅ {cantidad} unidades de {producto} añadidas por {usuario}.")

async def vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await update.message.reply_text("❌ No estás autorizado para usar este bot.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /vender <producto> <cantidad>")
        return
    producto = context.args[0].lower()
    cantidad = int(context.args[1])
    usuario = update.effective_user.username or update.effective_user.first_name

    if producto not in inventario or inventario[producto]["cantidad"] < cantidad:
        await update.message.reply_text("❌ No hay suficiente stock.")
        return

    inventario[producto]["cantidad"] -= cantidad
    inventario[producto]["ultima_accion"] = f"Vendido por {usuario}"

    guardar_inventario()
    await update.message.reply_text(f"🛒 {usuario} vendió {cantidad} unidades de {producto}.")

async def inventario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await update.message.reply_text("❌ No estás autorizado para usar este bot.")
        return
    await update.message.reply_text(f"📦 Inventario disponible aquí:\n{APP_URL}/inventario")

# ---------------- FLASK APP ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot de Inventario corriendo en Render"

@app.route("/inventario")
def ver_inventario():
    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Inventario</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="mb-4 text-center">📦 Inventario</h1>
            <table class="table table-striped table-bordered shadow">
                <thead class="table-dark">
                    <tr>
                        <th>Producto</th>
                        <th>Cantidad</th>
                        <th>Última acción</th>
                    </tr>
                </thead>
                <tbody>
                {% for producto, datos in inventario.items() %}
                    <tr>
                        <td>{{ producto }}</td>
                        <td>{{ datos['cantidad'] }}</td>
                        <td>{{ datos['ultima_accion'] }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, inventario=inventario)

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook(update: Update):
    telegram_app.update_queue.put_nowait(update)
    return "OK"

# ---------------- RUN BOT ----------------
async def run_bot():
    global telegram_app
    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("miid", miid))
    telegram_app.add_handler(CommandHandler("agregar", agregar))
    telegram_app.add_handler(CommandHandler("vender", vender))
    telegram_app.add_handler(CommandHandler("inventario", inventario_cmd))

    # Registrar webhook
    await telegram_app.bot.set_webhook(url=f"{APP_URL}/webhook/{BOT_TOKEN}")

    print("🤖 Bot escuchando con Webhook...")
    await telegram_app.start()

def start_bot():
    asyncio.run(run_bot())

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
