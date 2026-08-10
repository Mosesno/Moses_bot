import os
import re
import sys
import json
import random
import logging
import requests
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------------------------------------------------------
# Logging setup — replaces print() so you get real timestamps and
# stack traces in the PythonAnywhere log files.
# ---------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("moses_bot")

# ---------------------------------------------------------------
# Token: must come from the environment. No hardcoded placeholder —
# fail loudly and immediately instead of trying to run with a fake
# token and getting a confusing error from Telegram later.
# ---------------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN environment variable is not set. Exiting.")
    sys.exit(1)

QUESTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.json")

SURAH_NAMES = [
    "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف",
    "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم",
    "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء",
    "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل",
    "القصص", "العنكبوت", "الروم", "لقمان",
]

REQUEST_TIMEOUT = 10


# Arabic diacritics (tashkeel/harakat) unicode ranges — stripped so surah
# names always compare and display the same regardless of which marks the
# API happens to include on a given verse.
ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u08D4-\u08E1\u08E3-\u08FF]"
)


def normalize_surah_name(name):
    """Strip diacritics and a leading 'سورة' so surah names from the API
    and from SURAH_NAMES are always bare, plain text — otherwise
    formatting 'سورة {name}' later double-prefixes the API name (and/or
    mixes diacritic styles) and visually gives away the correct quiz
    answer."""
    stripped = ARABIC_DIACRITICS_RE.sub("", name).strip()
    if stripped.startswith("سورة"):
        stripped = stripped[len("سورة"):].strip()
    return stripped


def load_word_quizzes():
    """Load and validate the word-meaning quiz bank from questions.json.

    Returns an empty list (and logs why) instead of crashing the bot
    if the file is missing, malformed, or contains bad entries.
    """
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error("questions.json not found at %s", QUESTIONS_FILE)
        return []
    except json.JSONDecodeError as e:
        logger.error("questions.json is not valid JSON: %s", e)
        return []

    if not isinstance(data, list):
        logger.error("questions.json must contain a JSON array at the top level.")
        return []

    valid = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            logger.warning("Skipping entry %d: not an object.", i)
            continue
        question = entry.get("question")
        options = entry.get("options")
        correct = entry.get("correct")
        if not isinstance(question, str) or not question.strip():
            logger.warning("Skipping entry %d: missing/invalid 'question'.", i)
            continue
        if not isinstance(options, list) or len(options) < 2:
            logger.warning("Skipping entry %d: 'options' must be a list with 2+ items.", i)
            continue
        if not isinstance(correct, int) or not (0 <= correct < len(options)):
            logger.warning("Skipping entry %d: 'correct' index out of range.", i)
            continue
        valid.append(entry)

    if not valid:
        logger.warning("questions.json parsed but contained no valid entries.")
    return valid


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        BotCommand("start", "تشغيل البوت وعرض القائمة"),
        BotCommand("ayah", "آية عشوائية مكتوبة"),
        BotCommand("recitation", "آية عشوائية بصوت عبد الباسط"),
        BotCommand("quiz", "سؤال اسم السورة من الآية"),
        BotCommand("meaning", "سؤال معاني الكلمات القرآنية"),
    ]
    await context.bot.set_my_commands(commands)

    welcome_text = (
        "أهلاً بك! 👋\n\n"
        "أنا بوت يقدم آيات قرآنية، تلاوات، واختبارات تفاعلية.\n\n"
        "**الأوامر المتاحة:**\n"
        "• /ayah - آية عشوائية مكتوبة\n"
        "• /recitation - آية عشوائية بصوت عبد الباسط\n"
        "• /quiz - اختبار معرفة اسم السورة\n"
        "• /meaning - اختبار معاني الكلمات القرآنية\n"
        "• /start - عرض القائمة"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            "https://api.alquran.cloud/v1/ayah/random/ar.alafasy",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()["data"]
        text = data["text"]
        surah_name = data["surah"]["name"]
        ayah_num = data["numberInSurah"]

        message = f"﴿ {text} ﴾\n\n[سورة {surah_name} - الآية {ayah_num}]"
        await update.message.reply_text(message)
    except requests.RequestException as e:
        logger.error("Ayah API request failed: %s", e)
        await update.message.reply_text("تعذر الاتصال بمصدر الآيات حالياً، حاول لاحقاً.")
    except (KeyError, ValueError) as e:
        logger.error("Ayah response parsing failed: %s", e)
        await update.message.reply_text("حدث خطأ في قراءة البيانات، حاول مرة أخرى.")


async def recitation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            "https://api.alquran.cloud/v1/ayah/random/ar.abdulsamad",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()["data"]
        audio_url = data["audio"]
        surah_name = data["surah"]["name"]
        ayah_num = data["numberInSurah"]

        caption = f"🎙 بصوت الشيخ عبد الباسط عبد الصمد (مجود)\n📖 سورة {surah_name} - الآية {ayah_num}"
        await update.message.reply_audio(audio=audio_url, caption=caption)
    except requests.RequestException as e:
        logger.error("Recitation API request failed: %s", e)
        await update.message.reply_text("تعذر الاتصال بمصدر التلاوات حالياً، حاول لاحقاً.")
    except (KeyError, ValueError) as e:
        logger.error("Recitation response parsing failed: %s", e)
        await update.message.reply_text("حدث خطأ في قراءة البيانات، حاول مرة أخرى.")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            "https://api.alquran.cloud/v1/ayah/random/ar.alafasy",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()["data"]
        text = data["text"]
        correct_surah = normalize_surah_name(data["surah"]["name"])

        filtered_surahs = [s for s in SURAH_NAMES if s != correct_surah]
        wrong_options = random.sample(filtered_surahs, min(3, len(filtered_surahs)))

        options = wrong_options + [correct_surah]
        random.shuffle(options)

        correct_option_id = options.index(correct_surah)
        question = f"في أي سورة وردت هذه الآية الكريمة؟\n\n﴿ {text} ﴾"

        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=question[:290],
            options=[f"سورة {opt}"[:100] for opt in options],
            type="quiz",
            correct_option_id=correct_option_id,
            is_anonymous=False,
        )
    except requests.RequestException as e:
        logger.error("Quiz API request failed: %s", e)
        await update.message.reply_text("تعذر الاتصال بمصدر الآيات حالياً، حاول لاحقاً.")
    except (KeyError, ValueError) as e:
        logger.error("Quiz response parsing failed: %s", e)
        await update.message.reply_text("حدث خطأ في قراءة البيانات، حاول مرة أخرى.")


async def meaning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_word_quizzes()
    if not quizzes:
        await update.message.reply_text(
            "لا توجد أسئلة معاني متوفرة حالياً، تأكد من وجود ملف questions.json وصحة تنسيقه."
        )
        return

    quiz_data = random.choice(quizzes)
    try:
        # Shuffle options at send-time so the correct answer's position
        # doesn't leak from how questions.json happens to be authored
        # (many entries in the data have the correct answer first).
        indexed_options = list(enumerate(quiz_data["options"]))
        random.shuffle(indexed_options)
        shuffled_options = [opt for _, opt in indexed_options]
        new_correct_id = next(
            new_idx for new_idx, (orig_idx, _) in enumerate(indexed_options)
            if orig_idx == quiz_data["correct"]
        )

        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=quiz_data["question"][:290],
            options=[opt[:100] for opt in shuffled_options],
            type="quiz",
            correct_option_id=new_correct_id,
            is_anonymous=False,
        )
    except Exception as e:
        logger.exception("Failed to send meaning poll: %s", e)
        await update.message.reply_text("حدث خطأ أثناء إرسال سؤال المعاني، حاول مرة أخرى.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global fallback so an unexpected exception in any handler never
    crashes the whole bot process — it just gets logged."""
    logger.exception("Unhandled exception while processing update: %s", context.error)


def main():
    # Fail fast at startup if the questions file is broken, so you find
    # out from the PythonAnywhere console instead of from a silent
    # /meaning failure days later.
    quizzes = load_word_quizzes()
    logger.info("Loaded %d word-meaning quiz entries.", len(quizzes))

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayah", ayah))
    app.add_handler(CommandHandler("recitation", recitation))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("meaning", meaning))
    app.add_error_handler(on_error)

    logger.info("Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
