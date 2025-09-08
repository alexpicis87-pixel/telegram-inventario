from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
import os
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================
BOT_TOKEN = "6436352209:AAHH8IWy246pACneF3NPFhdJcsjkokmfOlU"
ADMIN_ID = 1886047632   # solo tú podrás ver ciertos comandos

DB_FILE = "inventario.db"

# =========================
# BASE DE DATOS
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            stock INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            tipo TEXT,
            cantidad INTEGER,
            persona TEXT,
            telegram TEXT,
            user_id INTEGER,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

def agregar_producto(nombre, cantidad, persona, telegram, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # si no existe el producto lo creamos
    c.execute("INSERT OR IGNORE INTO productos (nombre, stock) VALUES (?, 0)", (nombre,))
    c.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cantidad, nombre))

    movimiento = ("entrada", cantidad, persona, telegram, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    c.execute("INSERT INTO movimientos (producto, tipo, cantidad, persona, telegram, user_id, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (nombre, *movimiento))

    conn.commit()
    conn.close()

def vender_producto(nombre, cantidad, persona, telegram, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT stock FROM productos WHERE nombre = ?", (nombre,))
    row = c.fetchone()
    if not row or row[0] < cantidad:
        conn.close()
        return False, row[0] if row else 0

    c.execute("UPDATE productos SET stock = stock - ? WHERE nombre = ?", (cantidad, nombre))

    movimiento = ("salida", cantidad, persona, telegram, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    c.execute("INSERT INTO movimientos (producto, tipo, cantidad, persona, telegram, user_id, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (nombre, *movimiento))

    conn.commit()
    conn.close()
    return True, row[0] - cantidad

def obtener_inventario():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, stock FROM productos")
    datos = c.fetchall()
    conn.close()
    return datos

def obtener_historial(nombre):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT tipo, cantidad, persona, telegram, fecha FROM movimientos WHERE producto = ? ORDER BY id DESC LIMIT 10", (nombre,))
    datos = c.fetchall()
    conn.close()
    return datos

# =========================
# COMANDOS DEL BOT
# =========================
async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        cantidad = int(context.args[1])

        persona_input = " ".join(context.args[2:]) if len(context.args) > 2 else ""
        user = update.effective_user
        persona_telegram = user.username if user.username else user.first_name
        persona = persona_input if persona_input else persona_telegram

        agregar_producto(producto, cantidad, persona, persona_telegram, user.id)

        await update.message.reply_text(f"✅ {cantidad} {producto} agregado por {persona}.")
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

        exito, nuevo_stock = vender_producto(producto, cantidad, persona, persona_telegram, user.id)

        if exito:
            await update.message.reply_text(f"💸 {cantidad} {producto} vendido por {persona}.\n📦 Stock actual: {nuevo_stock}")
        else:
            await update.message.reply_text(f"⚠️ No hay suficiente stock de {producto}. Disponible: {nuevo_stock}")
    except:
        await update.message.reply_text("❌ Uso correcto: /vender producto cantidad persona")

async def inventario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = obtener_inventario()
    if not datos:
        await update.message.reply_text("📦 Inventario vacío.")
        return
    texto = "📊 *Inventario actual:*\n\n"
    for nombre, stock in datos:
        texto += f"- {nombre}: {stock} unidades\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso correcto: /historial producto")
        return

    producto = context.args[0].lower()
    datos = obtener_historial(producto)
    if not datos:
        await update.message.reply_text(f"⚠️ No hay historial para {producto}.")
        return

    texto = f"📜 *Historial de {producto}:*\n\n"
    for tipo, cantidad, persona, telegram, fecha in datos:
        simbolo = "➕" if tipo == "entrada" else "➖"
        texto += f"{simbolo} {cantidad} | {persona} ({telegram}) | {fecha}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# =========================
# MAIN
# =========================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("vender", vender))
    app.add_handler(CommandHandler("inventario", inventario_cmd))
    app.add_handler(CommandHandler("historial", historial))

    print("🤖 Bot de inventario en marcha...")
    app.run_polling()

if __name__ == "__main__":
    main()
