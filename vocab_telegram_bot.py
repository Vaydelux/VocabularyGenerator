import os
import json
import random
import asyncio
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_FILENAME = "vocab.json"  # Your JSON vocabulary file
BOT_USERNAME = None  # Will be set at startup

# === Load vocab ===
def load_vocab(filename=DEFAULT_FILENAME):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("❌ Failed to load vocab:", e)
        return []

# === Format vocab like idioms ===
def format_vocab(item: dict, index: int) -> str:
    word = f"*{telegram.helpers.escape_markdown(item['phrase'], version=2)}*"
    definition = f"💡 *Meaning:* _{telegram.helpers.escape_markdown(item['interpretation'], version=2)}_"

    example_lines = ["🧾 *Examples:*"]
    examples = item.get("examples", [])
    if examples:
        for i, ex in enumerate(examples, 1):
            example_lines.append(f"   ➤ _Example {i}:_ {telegram.helpers.escape_markdown(ex, version=2)}")
    else:
        example_lines.append("   ➤ _No examples available._")

    return f"🔹 *Word {index}*\n\n{word}\n\n{definition}\n\n" + "\n".join(example_lines)

# === Send vocab entries with delay and pinning ===
async def send_vocab(bot, chat_id, thread_id, vocab):
    for i, entry in enumerate(vocab, 1):
        msg_text = format_vocab(entry, i)

        msg = await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            message_thread_id=thread_id,
            parse_mode="MarkdownV2"
        )

        await asyncio.sleep(1.5)
        await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)
        await asyncio.sleep(1.5)

# === /start Handler ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None

    kwargs = {"message_thread_id": thread_id} if thread_id else {}
    await update.message.reply_text("⏳ Preparing 20 vocabulary words...", **kwargs)

    vocab = load_vocab()
    if not vocab:
        await context.bot.send_message(chat_id=chat_id, text="❌ Failed to load vocab.", **kwargs)
        return

    selected = random.sample(vocab, min(20, len(vocab)))
    await send_vocab(context.bot, chat_id, thread_id, selected)

    await context.bot.send_message(chat_id=chat_id, text="🎉 All words sent!", **kwargs)

# === Message fallback ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_USERNAME
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_input = update.message.text.lower()
    thread_id = update.message.message_thread_id

    if chat_type in ["group", "supergroup"] and f"@{BOT_USERNAME}" not in user_input:
        return

    kwargs = {"message_thread_id": thread_id} if thread_id else {}
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hi! Use /start to get vocabulary words with definitions 😊",
        **kwargs
    )

# === Main ===
if __name__ == "__main__":
    print("🤖 Bot running...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    async def startup(app):
        global BOT_USERNAME
        me = await app.bot.get_me()
        BOT_USERNAME = me.username.lower()
        print(f"✅ Bot username set to @{BOT_USERNAME}")

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = startup
    app.run_polling()
