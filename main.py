import os
import json
import random
import requests
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

# دالة لقراءة معاني الكلمات من ملف words.json الخارجي
def load_word_quizzes():
    try:
        with open("words.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading words.json: {e}")
        return []

# 1. أمر البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        BotCommand("start", "تشغيل البوت وعرض القائمة"),
        BotCommand("ayah", "آية عشوائية مكتوبة"),
        BotCommand("recitation", "آية عشوائية بصوت عبد الباسط"),
        BotCommand("quiz", "سؤال اسم السورة من الآية"),
        BotCommand("meaning", "سؤال معاني الكلمات القرآنية")
    ]
    await context.bot.set_my_commands(commands)

    welcome_text = (
        "أهلاً بك! 👋\n\n"
        "أنا بوت يقدم آيات قرآنية، تلاوات، وااختبارات تفاعلية.\n\n"
        "**الأوامر المتاحة:**\n"
        "• /ayah - آية عشوائية مكتوبة\n"
        "• /recitation - آية عشوائية بصوت عبد الباسط\n"
        "• /quiz - اختبار معرفة اسم السورة\n"
        "• /meaning - اختبار معاني الكلمات القرآنية\n"
        "• /start - عرض القائمة"
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
    except Exception:
        await update.message.reply_text("حدث خطأ، حاول مرة أخرى.")

# 3. أمر التلاوة الصوتية
async def recitation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.abdulsamad")
        if response.status_code == 200:
            data = response.json()["data"]
            audio_url = data["audio"]
            surah_name = data["surah"]["name"]
            ayah_num = data["numberInSurah"]
            
            caption = f"🎙 بصوت الشيخ عبد الباسط عبد الصمد (مجود)\n📖 سورة {surah_name} - الآية {ayah_num}"
            await update.message.reply_audio(audio=audio_url, caption=caption)
    except Exception:
        await update.message.reply_text("حدث خطأ، حاول مرة أخرى.")

# 4. أمر سؤال السورة (عشوائي من الـ API)
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.alafasy")
        if response.status_code == 200:
            data = response.json()["data"]
            text = data["text"]
            correct_surah = data["surah"]["name"]
            
            other_surahs = [
                "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", 
                "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", 
                "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء"
            ]
            
            filtered_surahs = [s for s in other_surahs if s != correct_surah]
            wrong_options = random.sample(filtered_surahs, 3)
            
            options = wrong_options + [correct_surah]
            random.shuffle(options)
            
            correct_option_id = options.index(correct_surah)
            question = f"في أي سورة وردت هذه الآية الكريمة؟\n\n﴿ {text} ﴾"
            
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=question[:300],
                options=[f"سورة {opt}" for opt in options],
                type="quiz",
                correct_option_id=correct_option_id,
                is_anonymous=False
            )
    except Exception:
        await update.message.reply_text("حدث خطأ، حاول مرة أخرى.")

# 5. أمر سؤال معاني الكلمات (من ملف words.json)
async def meaning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quizzes = load_word_quizzes()
        if not quizzes:
            await update.message.reply_text("لا توجد أسئلة معاني متوفرة حالياً.")
            return

        quiz_data = random.choice(quizzes)
        
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=quiz_data["question"],
            options=quiz_data["options"],
            type="quiz",
            correct_option_id=quiz_data["correct"],
            is_anonymous=False
        )
    except Exception:
        await update.message.reply_text("حدث خطأ أثناء إرسال سؤال المعاني، حاول مرة أخرى.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayah", ayah))
    app.add_handler(CommandHandler("recitation", recitation))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("meaning", meaning))
    
    app.run_polling()
