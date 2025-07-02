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
DEFAULT_FILENAME = "vocab.json"
BOT_USERNAME = None
VOCAB_DATA = []

# === Escape MarkdownV2 ===
def escape_md(text):
    return telegram.helpers.escape_markdown(str(text), version=2)

# === Format vocab ===
def format_vocab(item: dict, index: int) -> str:
    word = f"*{escape_md(item['phrase'])}*"
    definition = f"💡 *Meaning:* _{escape_md(item['interpretation'])}_"
    example_lines = ["🧾 *Examples:*"]
    examples = item.get("examples", [])
    if examples:
        for i, ex in enumerate(examples, 1):
            example_lines.append(f"   ➤ _Example {i}:_ {escape_md(ex)}")
    else:
        example_lines.append("   ➤ _No examples available._")
    return f"🔹 *Word {index}*\n\n{word}\n\n{definition}\n\n" + "\n".join(example_lines)

# === Send vocab entries ===
async def send_vocab(bot, chat_id, thread_id, vocab):
    for i, entry in enumerate(vocab, 1):
        msg_text = format_vocab(entry, i)
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=msg_text,
                message_thread_id=thread_id,
                parse_mode="MarkdownV2"
            )
            await asyncio.sleep(1.5)
            await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)
            await asyncio.sleep(1.5)
        except telegram.error.BadRequest as e:
            print(f"❌ Failed to send message {i}: {e}")
            continue

# === /start ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    kwargs = {"message_thread_id": thread_id} if thread_id else {}
    await update.message.reply_text("⏳ Preparing 20 vocabulary words...", **kwargs)

    if not VOCAB_DATA:
        await context.bot.send_message(chat_id=chat_id, text="❌ Vocab data not loaded.", **kwargs)
        return

    selected = random.sample(VOCAB_DATA, min(20, len(VOCAB_DATA)))
    await send_vocab(context.bot, chat_id, thread_id, selected)
    await context.bot.send_message(chat_id=chat_id, text="🎉 All words sent!", **kwargs)

# === /search ===
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    kwargs = {"message_thread_id": thread_id} if thread_id else {}
    if not context.args:
        await update.message.reply_text("Usage: /search <word>", **kwargs)
        return

    keyword = " ".join(context.args).lower()
    matches = [item for item in VOCAB_DATA if keyword in item['phrase'].lower()]
    if not matches:
        await update.message.reply_text("❌ No matching words found.", **kwargs)
        return

    await update.message.reply_text(f"🔎 Found {len(matches)} result(s). Showing up to 3:", **kwargs)
    await send_vocab(context.bot, chat_id, thread_id, matches[:3])

# === /page ===
async def page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    kwargs = {"message_thread_id": thread_id} if thread_id else {}

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /page <number>", **kwargs)
        return

    page_size = 20
    page = int(context.args[0])
    start = (page - 1) * page_size
    end = start + page_size
    chunk = VOCAB_DATA[start:end]

    if not chunk:
        await update.message.reply_text("❌ Page out of range.", **kwargs)
        return

    await update.message.reply_text(f"📖 Showing page {page}", **kwargs)
    await send_vocab(context.bot, chat_id, thread_id, chunk)

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
    menu = "📚 Commands Available:\n/start — Random 20 words\n/search <word> — Find a word\n/page <n> — Show page n (20 words per page)"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=menu, **kwargs)

# === Main ===
if __name__ == "__main__":
    print("🤖 Bot running...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    async def startup(app):
        global BOT_USERNAME, VOCAB_DATA
        me = await app.bot.get_me()
        BOT_USERNAME = me.username.lower()
        print(f"✅ Bot username set to @{BOT_USERNAME}")
        try:
            with open(DEFAULT_FILENAME, "r", encoding="utf-8") as f:
                VOCAB_DATA = json.load(f)
            print(f"📚 Loaded {len(VOCAB_DATA)} vocabulary entries.")
        except Exception as e:
            print(f"❌ Error loading vocab data: {e}")

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("page", page_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = startup
    app.run_polling()
