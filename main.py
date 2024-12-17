import logging
import requests
from telegram import Update, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
ALERTS = {}
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

# Function to fetch cryptocurrency price
def get_crypto_price(crypto_id, currency="usd"):
    """
    Fetch the current price of a cryptocurrency from CoinGecko API.
    :param crypto_id: The ID of the cryptocurrency (e.g., 'bitcoin', 'ethereum').
    :param currency: The currency for price conversion (e.g., 'usd', 'eur').
    :return: Current price or None if an error occurs.
    """
    try:
        response = requests.get(
            COINGECKO_API, params={"ids": crypto_id, "vs_currencies": currency}
        )
        response.raise_for_status()
        data = response.json()
        return data.get(crypto_id, {}).get(currency)
    except requests.RequestException as e:
        logger.error(f"Error fetching price: {e}")
        return None

# Start command handler
async def start(update: Update, context: CallbackContext):
    """
    Respond to the /start command with a welcome message.
    """
    await update.message.reply_text(
        "Welcome to the Crypto Price Bot! Use /price <crypto_id> to check prices.\n"
        "Example: /price bitcoin\n\n"
        "Use /alert <crypto_id> <target_price> to set alerts."
    )

# Price command handler
async def price(update: Update, context: CallbackContext):
    """
    Fetch and display the current price of a cryptocurrency.
    """
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /price <crypto_id>")
        return

    crypto_id = context.args[0].lower()
    price = get_crypto_price(crypto_id)
    if price is not None:
        await update.message.reply_text(
            f"The current price of {crypto_id.capitalize()} is ${price:.2f}."
        )
    else:
        await update.message.reply_text(f"Unable to fetch price for {crypto_id}.")

# Alert command handler
async def alert(update: Update, context: CallbackContext):
    """
    Set a price alert for a cryptocurrency.
    """
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /alert <crypto_id> <target_price>")
        return

    try:
        crypto_id = context.args[0].lower()
        target_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Target price must be a number.")
        return

    chat_id = update.effective_chat.id
    if chat_id not in ALERTS:
        ALERTS[chat_id] = []
    ALERTS[chat_id].append((crypto_id, target_price))

    await update.message.reply_text(
        f"Alert set for {crypto_id.capitalize()} at ${target_price:.2f}."
    )

# Function to check alerts
def check_alerts(context: CallbackContext):
    """
    Check if any alerts are triggered and notify users.
    """
    for chat_id, alerts in list(ALERTS.items()):
        for alert in alerts[:]:
            crypto_id, target_price = alert
            current_price = get_crypto_price(crypto_id)
            if current_price is not None and current_price >= target_price:
                context.bot.send_message(
                    chat_id,
                    f"🚨 Alert: {crypto_id.capitalize()} has reached ${current_price:.2f}!",
                )
                alerts.remove(alert)

        if not alerts:
            del ALERTS[chat_id]

# Main function
async def main():
    """
    Initialize the bot and start polling for updates.
    """
    application = (
        ApplicationBuilder()
        .token("YOUR_TELEGRAM_BOT_TOKEN")  # Replace with your bot token
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("alert", alert))

    # Schedule alerts
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: check_alerts(application.bot),
        "interval",
        seconds=30,
        id="check_alerts",
        replace_existing=True,
    )
    scheduler.start()

    await application.run_polling()

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
