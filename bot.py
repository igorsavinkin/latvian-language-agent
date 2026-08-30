import json
import logging
import os
import random

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# ============================================================
# Configuration
# ============================================================

VOCABULARY_FILE = "/app/vocabulary.json"
LESSON_CACHE_FILE = "/app/lesson_cache.json"

DEEPSEEK_MODEL = "deepseek-v4-flash"


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# DeepSeek client
# ============================================================

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)


# ============================================================
# Vocabulary
# ============================================================

def load_vocabulary():
    with open(VOCABULARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Lesson cache
# ============================================================

def save_lesson(lesson):
    with open(LESSON_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            lesson,
            f,
            ensure_ascii=False,
            indent=2,
        )


def load_cached_lesson():
    if not os.path.exists(LESSON_CACHE_FILE):
        return None

    try:
        with open(LESSON_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read lesson cache: %s", exc)
        return None


# ============================================================
# DeepSeek lesson generation
# ============================================================

def generate_lesson(words):

    vocabulary_text = "\n".join(
        f"- {word['lv']} — {word['ru']}"
        for word in words
    )

    prompt = f"""
You are an expert Latvian language teacher.

The student is a Russian-speaking learner of Latvian.

Create a short but useful Latvian grammar lesson using these
vocabulary items:

{vocabulary_text}

IMPORTANT RULES:

1. Use natural, modern Latvian.

2. You MAY change the grammatical form of the vocabulary word
   when this makes the example more useful for learning.

3. Identify the dictionary/base form (lemma).

4. Identify the grammatical form actually used in the sentence.

5. For nouns and adjectives:
   - specify case
   - specify number
   - specify gender when useful
   - use concise English terminology such as:
     "Dative plural"
     "Accusative singular"
     "Genitive plural"
     "Nominative singular"
     "Superlative, masculine singular"

6. For verbs:
   - specify person
   - number
   - tense
   - mood when relevant

7. For prepositions or indeclinable words:
   - give a short useful description, for example:
     "Preposition; governs dative"

8. Do NOT give long grammatical explanations.

9. The Russian translation supplied for the vocabulary item
   describes the intended meaning. Do not invent an unrelated meaning.

10. Every Latvian sentence must have a Russian translation.

11. The sentence should be useful for someone learning Latvian,
    preferably in a practical everyday or professional context.

12. Return ONLY valid JSON.
Do not use Markdown.
Do not put the JSON inside ``` fences.

Return exactly this structure:

{{
  "items": [
    {{
      "original_word": "...",
      "original_translation": "...",
      "lemma": "...",
      "part_of_speech": "...",
      "form_used": "...",
      "grammar": "...",
      "latvian_sentence": "...",
      "russian_translation": "...",
      "explanation_ru": "..."
    }}
  ]
}}
"""

    logger.info(
        "Generating lesson for words: %s",
        ", ".join(word["lv"] for word in words),
    )

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Latvian language teacher "
                    "for Russian-speaking students."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()

    # Remove Markdown fences if the model nevertheless adds them.
    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

        if content.startswith("json"):
            content = content[4:].strip()

    lesson = json.loads(content)

    if "items" not in lesson:
        raise ValueError("DeepSeek response does not contain 'items'")

    return lesson


# ============================================================
# /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        "🇱🇻 Latvian Vocabulary Trainer\n\n"
        "/words — show vocabulary\n"
        "/today — full lesson\n"
        "/short — short version of today's lesson\n"
        "/ping — test the bot"
    )


# ============================================================
# /ping
# ============================================================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if message is None:
        return

    await message.reply_text("🏓 Pong!")


# ============================================================
# /words
# ============================================================

async def words(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if message is None:
        return

    vocabulary = load_vocabulary()

    lines = ["🇱🇻 Your Latvian vocabulary:\n"]

    for i, word in enumerate(vocabulary, 1):
        lines.append(
            f"{i}. {word['lv']} — {word['ru']}"
        )

    await message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# /today
# ============================================================

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        "⏳ Preparing your Latvian lesson..."
    )

    try:
        vocabulary = load_vocabulary()

        if not vocabulary:
            raise ValueError("Vocabulary is empty")

        # Select up to 3 random words.
        selected_words = random.sample(
            vocabulary,
            min(3, len(vocabulary)),
        )

        lesson = generate_lesson(selected_words)

        # Save the lesson so /short can use exactly
        # the same lesson without another DeepSeek request.
        save_lesson(lesson)

        messages = [
            "🇱🇻 <b>>Jauni latviašu vardi</b>"
        ]

        for i, item in enumerate(lesson["items"], 1):

            messages.append(
                f"{i}. <b>{item['original_word']} — "
                f"{item['original_translation']}</b>\n\n"

                f"🔤 Lemma: {item['lemma']}\n"

                f"📚 Part of speech: "
                f"{item['part_of_speech']}\n"

                f"📝 Form: `{item['form_used']}`\n"

                f"📐 Grammar: {item['grammar']}\n\n"

                f"🇱🇻 {item['latvian_sentence']}\n"

                f"🇷🇺<tg-spoiler> {item['russian_translation']}</tg-spoiler>\n\n"

                f"💡 {item['explanation_ru']}"
            )

        await message.reply_text(
            "\n\n────────────\n\n".join(messages),
            parse_mode="HTML",
        )

    except Exception as exc:

        logger.exception(
            "Lesson generation failed: %s",
            exc,
        )

        await message.reply_text(
            "❌ Couldn't generate today's lesson.\n\n"
            "Please check the bot logs."
        )


# ============================================================
# /short
# ============================================================

async def short(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if message is None:
        return

    lesson = load_cached_lesson()

    if not lesson or "items" not in lesson:

        await message.reply_text(
            "ℹ️ No lesson has been generated yet.\n\n"
            "Use /today first."
        )

        return

    messages = [
        "🇱🇻 **Ātrs Latviešu vārdu atkārtojums**"
    ]

    for i, item in enumerate(lesson["items"], 1):

        messages.append(
            f"{i}.<b> {item['form_used']}</b> — "
            f"{item['original_translation']}\n"

            f"({item['grammar']})\n\n"

            f"🇱🇻 {item['latvian_sentence']}\n"

            f"🇷 <tg-spoiler> {item['russian_translation']}</tg-spoiler>"
        )

    await message.reply_text(
        "\n\n────────────\n\n".join(messages),
        parse_mode="HTML",
    )


# ============================================================
# Global error handler
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Exception while processing update: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# Main
# ============================================================

def main():

    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("ping", ping)
    )

    app.add_handler(
        CommandHandler("words", words)
    )

    app.add_handler(
        CommandHandler("today", today)
    )

    app.add_handler(
        CommandHandler("short", short)
    )

    app.add_error_handler(
        error_handler
    )

    logger.info("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
