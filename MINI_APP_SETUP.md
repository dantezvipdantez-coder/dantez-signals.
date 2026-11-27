# DANTEZ SIGNALS — Telegram Mini App

## Mini App frontend

The Telegram Mini App interface is in `webapp/index.html`. It currently provides the terminal layout and client-side selectors for market, asset, timeframe, and expiry. Live chart data and signal requests are not connected yet; the page intentionally does not fabricate market data.

## Publish with GitHub Pages

1. Open the repository **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Open the **Actions** tab and check the **Deploy Telegram Mini App** workflow.
4. After a successful deployment, copy the published Pages URL from the workflow deployment environment.

The workflow deploys the contents of `webapp/` whenever that folder changes on `main`.

## Connect the Telegram bot

Set the environment variable `WEBAPP_URL` in the bot hosting service to the exact HTTPS URL published by GitHub Pages. Keep the existing `BOT_TOKEN` environment variable secret. Restart or redeploy the bot after changing environment variables.

The bot will then show an **Открыть DANTEZ Mini App** button in its `/start` menu. Telegram requires an HTTPS URL for the Mini App.

## Current implementation status

- [x] Initial premium Mini App interface
- [x] Telegram Web App SDK initialization
- [x] Market, asset, timeframe, and expiry selectors
- [x] GitHub Actions workflow for GitHub Pages
- [x] Bot-side Mini App launch button controlled by `WEBAPP_URL`
- [ ] Connect Mini App controls to a trusted backend endpoint
- [ ] Display real OHLC candles from the configured market-data provider
- [ ] Return analysis results to the Mini App

Do not put the Telegram bot token in frontend JavaScript. All market-data requests and bot credentials must remain server-side.
