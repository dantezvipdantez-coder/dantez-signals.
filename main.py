
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

MARKETS = {
    "forex": "Forex",
    "otc": "OTC",
    "crypto": "Криптовалюты",
    "crypto_idx": "Crypto IDX",
    "altcoin_idx": "Altcoin IDX",
}

ASSETS = {
    "forex": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
              "USD/CAD", "EUR/JPY"],
    "otc": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC",
            "AUD/USD OTC", "EUR/JPY OTC"],
    "crypto": ["BTC/USDT", "ETH/USDT", "BNB/USDT",
               "SOL/USDT", "XRP/USDT"],
}

def make_keyboard(items, prefix):
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"{prefix}:{key}")]
        for key, name in items
    ]
    return InlineKeyboardMarkup(buttons)


def timeframe_keyboard():
    return make_keyboard(
        [(x, x) for x in ["M1", "M5", "M15"]],
        "time"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "DANTEZ SIGNALS\n\nВыбери рынок:",
        reply_markup=make_keyboard(list(MARKETS.items()), "market")
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, value = query.data.split(":", 1)

    if action == "market":
        context.user_data["market_key"] = value
        context.user_data["market"] = MARKETS[value]

        assets = ASSETS.get(value, [])

        items = [(str(i), asset) for i, asset in enumerate(assets)]
        items.append(("custom", "Ввести свой актив"))

        await query.edit_message_text(
            f"Рынок: {MARKETS[value]}\n\nВыбери актив:",
            reply_markup=make_keyboard(items, "asset")
        )

    elif action == "asset":
        if value == "custom":
            context.user_data["awaiting_asset"] = True
            await query.edit_message_text(
                "Напиши название актива или валютную пару.\n\n"
                "Например: EUR/USD, GBP/JPY, BTC/USDT."
            )
            return

        market_key = context.user_data["market_key"]
        context.user_data["asset"] = ASSETS[market_key][int(value)]

        await query.edit_message_text(
            f"Актив: {context.user_data['asset']}\n\nВыбери таймфрейм:",
            reply_markup=timeframe_keyboard()
        )

    elif action == "time":
        context.user_data["timeframe"] = value

        items = [
            (x, x) for x in
            ["1 минута", "2 минуты", "3 минуты", "5 минут"]
        ]

        await query.edit_message_text(
            "Выбери срок экспирации:",
            reply_markup=make_keyboard(items, "expiry")
        )

    elif action == "expiry":
        context.user_data["expiry"] = value

        await query.edit_message_text(
            "DANTEZ SIGNALS — настройки сохранены\n\n"
            f"Рынок: {context.user_data['market']}\n"
            f"Актив: {context.user_data['asset']}\n"
            f"Таймфрейм: {context.user_data['timeframe']}\n"
            f"Экспирация: {value}\n\n"
            "Реальный анализ пока не подключён.",
            reply_markup=make_keyboard(
                [("back", "Выбрать другой актив")],
                "nav"
            )
        )

    elif action == "nav" and value == "back":
        await query.edit_message_text(
            "Выбери рынок:",
            reply_markup=make_keyboard(list(MARKETS.items()), "market")
        )


async def custom_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_asset"):
        return

    asset = update.message.text.strip().upper()

    if len(asset) < 2 or len(asset) > 30:
        await update.message.reply_text(
            "Название должно содержать от 2 до 30 символов. Попробуй ещё раз."
        )
        return

    context.user_data["asset"] = asset
    context.user_data["awaiting_asset"] = False

    await update.message.reply_text(
        f"Выбран актив: {asset}\n\nВыбери таймфрейм:",
        reply_markup=timeframe_keyboard()
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Выбор сброшен. Для нового выбора отправь /start."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — открыть меню\n"
        "/stop — сбросить выбор\n"
        "/help — помощь"
    )


def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(menu))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, custom_asset)
    )

    print("DANTEZ SIGNALS запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
                          
