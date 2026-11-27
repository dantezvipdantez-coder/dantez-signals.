import os
import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta

import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
API = "https://biquote.io/api"

MARKETS = {
    "forex": "Forex",
    "otc": "OTC",
    "crypto": "Криптовалюты",
    "crypto_idx": "Crypto IDX",
    "altcoin_idx": "Altcoin IDX",
}

ASSETS = {
    "forex": [
        "EUR/USD", "GBP/USD", "USD/JPY",
        "AUD/USD", "USD/CAD", "EUR/JPY"
    ],
    "otc": [
        "EUR/USD OTC", "GBP/USD OTC",
        "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC"
    ],
    "crypto": [
        "BTC/USDT", "ETH/USDT", "BNB/USDT",
        "SOL/USDT", "XRP/USDT"
    ],
}

TIMEFRAMES = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
}

EXPIRIES = ["1 минута", "2 минуты", "3 минуты", "5 минут"]


def keyboard(items, prefix):
    buttons = [
        [InlineKeyboardButton(
            name, callback_data=f"{prefix}:{key}"
        )]
        for key, name in items
    ]
    return InlineKeyboardMarkup(buttons)


def timeframe_keyboard():
    return keyboard(
        [(x, x) for x in TIMEFRAMES],
        "time"
    )


def main_menu_keyboard():
    return keyboard(list(MARKETS.items()), "market")


def action_keyboard():
    return keyboard([
        ("analyze", "Провести анализ"),
        ("back", "Выбрать другой актив"),
    ], "action")


def ema_series(values, period):
    result = [None] * len(values)

    if len(values) < period:
        return result

    current = sum(values[:period]) / period
    result[period - 1] = current

    multiplier = 2 / (period + 1)

    for i in range(period, len(values)):
        current = (
            values[i] * multiplier
            + current * (1 - multiplier)
        )
        result[i] = current

    return result


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            avg_gain * (period - 1) + gains[i]
        ) / period

        avg_loss = (
            avg_loss * (period - 1) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_market_data(asset, timeframe):
    symbol = asset.replace("/", "").upper()

    if not re.fullmatch(r"[A-Z0-9]{6,12}", symbol):
        raise ValueError("Некорректное название актива.")

    interval = TIMEFRAMES[timeframe]

    headers = {"User-Agent": "DANTEZ-SIGNALS/1.0"}

    quote_response = requests.get(
        f"{API}/{symbol}",
        headers=headers,
        timeout=12
    )
    quote_response.raise_for_status()
    quote = quote_response.json()

    if quote.get("stale") is True:
        raise ValueError("Котировка устарела.")

    if quote.get("marketState") != "open":
        raise ValueError("Рынок закрыт или данные недоступны.")

    quote_age = quote.get("quoteAgeSeconds")

    if quote_age is not None and float(quote_age) > 180:
        raise ValueError("Последняя котировка слишком старая.")

    response = requests.get(
        f"{API}/{symbol}/ohlc",
        params={"interval": interval, "limit": 300},
        headers=headers,
        timeout=15
    )
    response.raise_for_status()

    data = response.json()
    bars = data.get("bars", [])

    if not isinstance(bars, list):
        raise ValueError("Неверный формат свечей.")

    completed = []

    for bar in bars:
        if bar.get("isOpen") is not False:
            continue

        try:
            close = float(bar["close"])
            open_time = datetime.fromisoformat(
                bar["openTime"].replace("Z", "+00:00")
            )

            completed.append({
                "close": close,
                "openTime": open_time,
            })

        except (KeyError, TypeError, ValueError):
            continue

    completed.sort(key=lambda x: x["openTime"])

    if len(completed) < 60:
        raise ValueError(
            "Недостаточно закрытых свечей для анализа."
        )

    minutes = int(timeframe[1:])
    last_bar = completed[-1]

    candle_close_time = (
        last_bar["openTime"] + timedelta(minutes=minutes)
    )

    age = (
        datetime.now(timezone.utc) - candle_close_time
    ).total_seconds()

    if age < -60 or age > minutes * 60 * 3:
        raise ValueError("Свечи устарели. Анализ отменён.")

    return [bar["close"] for bar in completed], last_bar


def analyze_market(asset, timeframe, expiry):
    closes, last_bar = get_market_data(asset, timeframe)

    ema9 = ema_series(closes, 9)
    ema21 = ema_series(closes, 21)

    rsi = calculate_rsi(closes)

    fast = ema_series(closes, 12)
    slow = ema_series(closes, 26)

    macd_values = [
        fast[i] - slow[i]
        for i in range(len(closes))
        if fast[i] is not None and slow[i] is not None
    ]

    signal_values = ema_series(macd_values, 9)

    if not signal_values or signal_values[-1] is None:
        raise ValueError("Недостаточно данных для MACD.")

    macd = macd_values[-1]
    macd_signal = signal_values[-1]
    histogram = macd - macd_signal

    e9 = ema9[-1]
    e21 = ema21[-1]

    if rsi is None or e9 is None or e21 is None:
        raise ValueError("Не удалось рассчитать индикаторы.")

    up = (
        e9 > e21
        and 52 < rsi < 68
        and macd > macd_signal
        and histogram > 0
    )

    down = (
        e9 < e21
        and 32 < rsi < 48
        and macd < macd_signal
        and histogram < 0
    )

    if up:
        direction = "UP ↑"
        explanation = "Индикаторы показывают согласованность в пользу роста."
    elif down:
        direction = "DOWN ↓"
        explanation = "Индикаторы показывают согласованность в пользу снижения."
    else:
        direction = "NO TRADE"
        explanation = "Индикаторы не дают достаточного согласованного подтверждения."

    return (
        direction,
        explanation,
        e9,
        e21,
        rsi,
        macd,
        macd_signal,
        last_bar["openTime"],
        expiry,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "DANTEZ SIGNALS\n\nВыбери рынок:",
        reply_markup=main_menu_keyboard()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, value = query.data.split(":", 1)

    if action == "market":
        context.user_data["market_key"] = value
        context.user_data["market"] = MARKETS[value]

        assets = ASSETS.get(value, [])

        items = [
            (str(i), asset)
            for i, asset in enumerate(assets)
        ]

        items.append(("custom", "Ввести свой актив"))

        await query.edit_message_text(
            f"Рынок: {MARKETS[value]}\n\nВыбери актив:",
            reply_markup=keyboard(items, "asset")
        )

    elif action == "asset":
        if value == "custom":
            context.user_data["awaiting_asset"] = True

            await query.edit_message_text(
                "Введи валютную пару.\n"
                "Например: EUR/USD или GBP/JPY."
            )
            return

        market_key = context.user_data["market_key"]

        context.user_data["asset"] = ASSETS[market_key][int(value)]

        await query.edit_message_text(
            f"Актив: {context.user_data['asset']}\n\n"
            "Выбери таймфрейм:",
            reply_markup=timeframe_keyboard()
        )

    elif action == "time":
        context.user_data["timeframe"] = value

        await query.edit_message_text(
            "Выбери срок экспирации:",
            reply_markup=keyboard(
                [(x, x) for x in EXPIRIES],
                "expiry"
            )
        )

    elif action == "expiry":
        context.user_data["expiry"] = value

        await query.edit_message_text(
            "Настройки сохранены.\n\n"
            f"Рынок: {context.user_data['market']}\n"
            f"Актив: {context.user_data['asset']}\n"
            f"Таймфрейм: {context.user_data['timeframe']}\n"
            f"Экспирация: {value}\n\n"
            "Нажми кнопку для анализа.",
            reply_markup=action_keyboard()
        )

    elif action == "action":
        if value == "back":
            await query.edit_message_text(
                "Выбери рынок:",
                reply_markup=main_menu_keyboard()
            )
            return

        await run_analysis(query, context)


async def custom_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_asset"):
        return

    asset = update.message.text.strip().upper()

    if not re.fullmatch(r"[A-Z]{3}/?[A-Z]{3}", asset):
        await update.message.reply_text(
            "Неверный формат. Пример: EUR/USD."
        )
        return

    if "/" not in asset:
        asset = asset[:3] + "/" + asset[3:]

    context.user_data["asset"] = asset
    context.user_data["awaiting_asset"] = False

    await update.message.reply_text(
        f"Выбран актив: {asset}\n\n"
        "Выбери таймфрейм:",
        reply_markup=timeframe_keyboard()
    )


async def run_analysis(query, context):
    market = context.user_data.get("market_key")

    if market != "forex":
        await query.message.reply_text(
            "Для этого рынка источник котировок пока не подключён.\n"
            "Чтобы не выдавать ложные сигналы, анализ отменён."
        )
        return

    asset = context.user_data.get("asset")
    timeframe = context.user_data.get("timeframe")
    expiry = context.user_data.get("expiry")

    if not all([asset, timeframe, expiry]):
        await query.message.reply_text(
            "Сначала выбери актив, таймфрейм и экспирацию через /start."
        )
        return

    await query.message.reply_text(
        "Получаю котировки и анализирую закрытые свечи..."
    )

    try:
        result = await asyncio.to_thread(
            analyze_market,
            asset,
            timeframe,
            expiry
        )

        (
            direction,
            explanation,
            e9,
            e21,
            rsi,
            macd,
            macd_signal,
            candle_time,
            selected_expiry,
        ) = result

        candle_text = candle_time.strftime("%H:%M UTC")

        message = (
            "DANTEZ SIGNALS\n\n"
            f"Актив: {asset}\n"
            f"Рынок: Forex\n"
            f"Таймфрейм: {timeframe}\n\n"
            f"Результат: {direction}\n"
            f"{explanation}\n\n"
            "ИНДИКАТОРЫ\n"
            f"EMA 9: {e9:.6f}\n"
            f"EMA 21: {e21:.6f}\n"
            f"RSI 14: {rsi:.2f}\n"
            f"MACD: {macd:.7f}\n"
            f"MACD Signal: {macd_signal:.7f}\n\n"
            f"Последняя закрытая свеча: {candle_text}\n"
            f"Выбранная экспирация: {selected_expiry}\n\n"
            "Экспирация выбрана тобой, а не рассчитана "
            "как гарантированно подходящая.\n"
            "Результат анализа не гарантирует исход сделки."
        )

        await query.message.reply_text(message)

    except requests.RequestException:
        logging.exception("Market API error")

        await query.message.reply_text(
            "Не удалось получить данные рынка. "
            "Попробуй позже."
        )

    except (ValueError, KeyError, TypeError):
        logging.exception("Analysis error")

        await query.message.reply_text(
            "Анализ отменён: данные устарели, неполные "
            "или имеют неверный формат."
        )

    except Exception:
        logging.exception("Unexpected error")

        await query.message.reply_text(
            "Произошла внутренняя ошибка анализа."
        )


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("asset"):
        await update.message.reply_text(
            "Сначала настрой актив через /start."
        )
        return

    class MessageQuery:
        message = update.message

    await run_analysis(MessageQuery(), context)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Настройки сброшены. Отправь /start."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — выбор рынка и актива\n"
        "/analyze — провести анализ\n"
        "/stop — сбросить настройки\n"
        "/help — помощь"
    )


def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CallbackQueryHandler(menu))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, custom_asset)
    )

    print("DANTEZ SIGNALS запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
