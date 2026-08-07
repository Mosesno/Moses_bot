import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# جلب التوكن من متغيرة البيئة
TOKEN = os.environ.get("BOT_TOKEN")

async def ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # جلب آية عشوائية باللغة العربية
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.alafasy")
        if response.status_code == 200:
            data = response.json()["data"]
            text = data["text"]
            surah_name = data["surah"]["name"]
            ayah_num = data["numberInSurah"]
            
            message = f"﴿ {text} ﴾\n\n[سورة {surah_name} - الآية {ayah_num}]"
            await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text("حدث خطأ أثناء جلب الآية، حاول مرة أخرى.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("ayah", ayah))
    app.run_polling()
