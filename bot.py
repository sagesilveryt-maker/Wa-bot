import requests
import asyncio
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ID_INSTANCE = os.getenv("ID_INSTANCE")
API_TOKEN = os.getenv("API_TOKEN")

MENU, ENTER_NUMBER, CHECK_INPUT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📱 Pair WhatsApp"],
        ["🔍 Check Numbers (Text)"],
        ["📂 Check Numbers (TXT File)"],
        ["📊 Status"]
    ]
    await update.message.reply_text(
        "⚡ WhatsApp Control Panel",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📱 Pair WhatsApp":
        await update.message.reply_text("Send number (e.g. 919876543210)")
        return ENTER_NUMBER

    elif text == "🔍 Check Numbers (Text)":
        await update.message.reply_text("Send numbers separated by space")
        return CHECK_INPUT

    elif text == "📂 Check Numbers (TXT File)":
        await update.message.reply_text("Upload .txt file")
        return CHECK_INPUT

    elif text == "📊 Status":
        await update.message.reply_text("✅ Bot running (deployed)")
        return MENU

    return MENU

async def pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/GetAuthorizationCode/{API_TOKEN}"
    res = requests.post(url, json={"phoneNumber": phone})

    if res.status_code == 200:
        code = res.json().get("code", "No code")
        await update.message.reply_text(f"✅ Code:\n\n`{code}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Error")

    return MENU

async def process_numbers(update, numbers):
    valid, invalid = [], []

    for i, num in enumerate(numbers, 1):
        try:
            res = requests.post(
                f"https://api.green-api.com/waInstance{ID_INSTANCE}/CheckWhatsapp/{API_TOKEN}",
                json={"phoneNumber": num}
            )

            if res.status_code == 200 and res.json().get("exists"):
                valid.append(num)
            else:
                invalid.append(num)

        except:
            invalid.append(num)

        await asyncio.sleep(0.1)

        if i % 10 == 0:
            await update.message.reply_text(f"⏳ {i}/{len(numbers)}")

    return valid, invalid

async def send_results(update, valid, invalid):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    v_file = f"valid_{ts}.txt"
    i_file = f"invalid_{ts}.txt"

    with open(v_file, "w") as f:
        f.write("\n".join(valid))

    with open(i_file, "w") as f:
        f.write("\n".join(invalid))

    await update.message.reply_document(open(v_file, "rb"), filename=v_file)
    await update.message.reply_document(open(i_file, "rb"), filename=i_file)

    os.remove(v_file)
    os.remove(i_file)

async def check_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numbers = update.message.text.split()
    await update.message.reply_text("⚡ Checking...")
    v, i = await process_numbers(update, numbers)
    await send_results(update, v, i)
    return MENU

async def check_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = "numbers.txt"
    await file.download_to_drive(path)

    with open(path) as f:
        numbers = [x.strip() for x in f if x.strip()]

    await update.message.reply_text(f"Loaded {len(numbers)} numbers")

    v, i = await process_numbers(update, numbers)
    await send_results(update, v, i)

    return MENU

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, pair)],
            CHECK_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_text),
                MessageHandler(filters.Document.ALL, check_file)
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv)

    print("🚀 Bot deployed...")
    app.run_polling()

if __name__ == "__main__":
    main()
