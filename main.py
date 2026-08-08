import os
import requests
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

# 1. أمر البداية والتكشيف
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        BotCommand("start", "تشغيل البوت وعرض القائمة"),
        BotCommand("ayah", "آية عشوائية مكتوبة"),
        BotCommand("recitation", "آية عشوائية بصوت عبد الباسط (مجود)")
    ]
    await context.bot.set_my_commands(commands)

    welcome_text = (
        "أهلاً بك! 👋\n\n"
        "أنا بوت يقدم آيات قرآنية عشوائية مكتوبة وصوتية (تلاوة مجودة).\n\n"
        "**الأوامر المتاحة:**\n"
        "• /ayah - إرسال آية عشوائية مكتوبة\n"
        "• /recitation - إرسال آية عشوائية مجودة بصوت الشيخ عبد الباسط\n"
        "• /start - عرض هذه الرسالة التعريفية"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 2. أمر الآية المكتوبة
async def ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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

# 3. أمر الآية الصوتية (عبد الباسط عبد الصمد - تجويد)
async def recitation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # استدعاء API الآيات المجودة للشيخ عبد الباسط
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.abdulsamad")
        if response.status_code == 200:
            data = response.json()["data"]
            audio_url = data["audio"]
            surah_name = data["surah"]["name"]
            ayah_num = data["numberInSurah"]
            
            caption = f"🎙 بصوت الشيخ عبد الباسط عبد الصمد (تلاوة مجودة)\n📖 سورة {surah_name} - الآية {ayah_num}"
            
            await update.message.reply_audio(audio=audio_url, caption=caption)
    except Exception as e:
        await update.message.reply_text("حدث خطأ أثناء جلب التلاوة الصوتية، حاول مرة أخرى.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayah", ayah))
    app.add_handler(CommandHandler("recitation", recitation))
    
    app.run_polling()
