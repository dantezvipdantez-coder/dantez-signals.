import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
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

def keyboard(items, prefix):
    buttons = [
        [InlineKeyboardButton(item, callback_data=f"{prefix}:{key}")]
        for key, item in items
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "DANTEZ SIGNALS\n\nВыбери рынок:",
        reply_markup=keyboard(list(MARKETS.items()), "market")
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split(":", 1)
    action, value = data[0], data[1]

    if action == "market":
        context.user_data["market"] = MARKETS[value]

        if value in ASSETS:
            items = [(str(i), asset)
                     for i, asset in enumerate(ASSETS[value])]
            await query.edit_message_text(
                f"Рынок: {MARKETS[value]}\n\nВыбери актив:",
                reply_markup=keyboard(items, "asset")
            )
        else:
            await query.edit_message_text(
                f"Выбран {MARKETS[value]}.\n\n"
                "Список доступных инструментов нужно сверить "
                "с платформой Binomo перед подключением сигналов.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Назад", callback_data="back")
                ]])
            )

    elif action == "asset":
        market = context.user_data.get("market", "")
        context.user_data["asset"] = ASSETS[
            next(k for k, v in MARKETS.items() if v == market)
        ][int(value)]

        items = [(x, x) for x in ["M1", "M5", "M15"]]
        await query.edit_message_text(
            f"Актив: {context.user_data['asset']}\n\n"
            "Выбери таймфрейм:",
            reply_markup=keyboard(items, "time")
        )

    elif action == "time":
        context.user_data["timeframe"] = value

        items = [(x, x) for x in ["1 минута", "2 минуты",
                                  "3 минуты", "5 минут"]]
        await query.edit_message_text(
            f"Таймфрейм: {value}\n\nВыбери срок экспирации:",
            reply_markup=keyboard(items, "expiry")
        )

    elif action == "expiry":
        context.user_data["expiry"] = value

        await query.edit_message_text(
            "DANTEZ SIGNALS — настройки сохранены\n\n"
            f"Рынок: {context.user_data['market']}\n"
            f"Актив: {context.user_data['asset']}\n"
            f"Таймфрейм: {context.user_data['timeframe']}\n"
            f"Экспирация: {value}\n\n"
            "Анализ рынка и реальные сигналы пока не подключены.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Новий выбор", callback_data="back")
            ]])
        )

    elif action == "back":
        await query.edit_message_text(
            "DANTEZ SIGNALS\n\nВыбери рынок:",
            reply_markup=keyboard(list(MARKETS.items()), "market")
        )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Текущий выбор сброшен. Для нового выбора отправь /start."
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

    print("DANTEZ SIGNALS запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
        
