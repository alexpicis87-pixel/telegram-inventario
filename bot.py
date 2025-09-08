import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Token de tu bot
BOT_TOKEN = "6436352209:AAHH8IWy246pACneF3NPFhdJcsjkokmfOlU"

# Archivo donde se guarda el inventario
ARCHIVO = "inventario.json"

# Cargar inventario
if os.path.exists(ARCHIVO):
    with open(ARCHIVO, "r") as f:
        inventario = json.load(f)
else:
    inventario = {}

def guardar():
    with open(ARCHIVO, "w") as f:
        json.dump(inventario, f, indent=4)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bienvenido al Bot de Inventario.\nUsa /agregar, /vender, /inventario, /historial")

# /agregar producto cantidad persona
async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        cantidad = int(context.args[1])
        persona_input = " ".join(context.args[2:]) if len(context.args) > 2 else ""

        user = update.effective_user
        persona_telegram = user.username if user.username else user.first_name
        persona = persona_input if persona_input else persona_telegram

        if producto not in inventario:
            inventario[producto] = {"stock": 0, "movimientos": []}
        inventario[producto]["stock"] += cantidad
        inventario[producto]["movimientos"].append(
            f"+{cantidad} agregado por {persona} (Telegram: {persona_telegram}, ID: {user.id})"
        )

        guardar()
        await update.message.reply_text(f"✅ {cantidad} {producto} agregado.\n📦 Stock actual: {inventario[producto]['stock']}")
    except:
        await update.message.reply_text("❌ Uso correcto: /agregar producto cantidad persona")

# /vender producto cantidad persona
async def vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        cantidad = int(context.args[1])
        persona_input = " ".join(context.args[2:]) if len(context.args) > 2 else ""

        user = update.effective_user
        persona_telegram = user.username if user.username else user.first_name
        persona = persona_input if persona_input else persona_telegram

        if producto not in inventario or inventario[producto]["stock"] < cantidad:
            await update.message.reply_text("⚠️ No hay suficiente stock o el producto no existe.")
            return

        inventario[producto]["stock"] -= cantidad
        inventario[producto]["movimientos"].append(
            f"-{cantidad} vendido por {persona} (Telegram: {persona_telegram}, ID: {user.id})"
        )

        guardar()
        await update.message.reply_text(f"💸 {cantidad} {producto} vendido.\n📦 Stock actual: {inventario[producto]['stock']}")
    except:
        await update.message.reply_text("❌ Uso correcto: /vender producto cantidad persona")

# /inventario
async def inventario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not inventario:
        await update.message.reply_text("📦 Inventario vacío.")
        return

    texto = "📊 Inventario actual:\n"
    for prod, data in inventario.items():
        texto += f"- {prod}: {data['stock']} unidades\n"
    await update.message.reply_text(texto)

# /historial producto
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        producto = context.args[0].lower()
        if producto not in inventario:
            await update.message.reply_text("⚠️ Ese producto no existe en el inventario.")
            return
        movimientos = inventario[producto]["movimientos"]
        if not movimientos:
            await update.message.reply_text("📜 Sin movimientos aún.")
            return
        texto = f"📜 Historial de {producto}:\n" + "\n".join(movimientos)
        await update.message.reply_text(texto)
    except:
        await update.message.reply_text("❌ Uso correcto: /historial producto")

# Main
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("vender", vender))
    app.add_handler(CommandHandler("inventario", inventario_cmd))
    app.add_handler(CommandHandler("historial", historial))

    print("🤖 Bot de inventario en marcha...")
    app.run_polling()

if __name__ == "__main__":
    main()
