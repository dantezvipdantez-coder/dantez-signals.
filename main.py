
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Forex", callback_data="forex")],
        [InlineKeyboardButton("OTC", callback_data="otc")],
        [InlineKeyboardButton("Криптовалюты", callback_data="crypto")],
        [InlineKeyboardButton("Crypto IDX", callback_data="crypto_idx")],
        [InlineKeyboardButton("Altcoin IDX", callback_data="altcoin_idx")],
    ]

    await update.message.reply_text(
        "DANTEZ SIGNALS\n\n"
        "Выбери интересующий рынок:\n\n"
        "После выбора добавим список активов и таймфреймы.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    markets = {
        "forex": "Forex",
        "otc": "OTC",
        "crypto": "Криптовалюты",
        "crypto_idx": "Crypto IDX",
        "altcoin_idx": "Altcoin IDX",
    }

    market = markets.get(query.data)

    if market:
        context.user_data["market"] = market
        await query.edit_message_text(
            f"Выбран рынок: {market}\n\n"
            "Список доступных активов подключим следующим этапом.\n"
            "Реальные сигналы пока не активированы."
        )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Уведомления остановлены. Чтобы открыть меню снова, отправь /start."
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "DANTEZ SIGNALS\n\n"
        "/start — открыть меню\n"
        "/stop — остановить уведомления\n"
        "/help — помощь"
    )


def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("DANTEZ SIGNALS запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
  
