import gspread
from google.oauth2.service_account import Credentials

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ================== CONFIGURATION ==================

# Path to the JSON key you downloaded from Google Cloud
SERVICE_ACCOUNT_FILE = "service_account.json"

# Your Google Sheet ID (from the URL)
SPREADSHEET_ID = "1KVjWa9t0PreTec_EiF6-XXf1nxJ5CLYmGJ7QDGz844Q"

# Sheet tab name (bottom of Google Sheets, default is "Sheet1")
SHEET_NAME = "Expenses"

# Your Telegram bot token from BotFather
BOT_TOKEN = "7512914899:AAHHcCxS4iwoQB3DUIzaPLe0tqWQ2mHPfTo"

# ================== GOOGLE SHEETS SETUP ==================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


def add_expense_from_text(text: str):
    """
    Expects text like: 'Coffee, 120, Cash'
    Splits it into Item, Amount, Payment_Type and appends to Google Sheet.
    """
    parts = [p.strip() for p in text.split(",")]

    if len(parts) != 3:
        raise ValueError(
            "Invalid format.\nUse: Item, Amount, Payment_Type\n"
            "Example: Coffee, 120, Cash"
        )

    item, amount_str, payment_type = parts

    # Validate amount
    try:
        amount = float(amount_str)
    except ValueError:
        raise ValueError("Amount must be a number. Example: Coffee, 120, Cash")

    row = [item, str(amount), payment_type]
    sheet.append_row(row)
    return row

# ================== TELEGRAM BOT HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /start command."""
    await update.message.reply_text(
        "Hi! 👋\n"
        "Send me your expense in this format:\n\n"
        "Item, Amount, Payment_Type\n\n"
        "Example:\nCoffee, 120, Cash"
    )


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle normal text messages as expenses."""
    text = update.message.text

    try:
        row = add_expense_from_text(text)
        item, amount, payment_type = row
        await update.message.reply_text(
            f"✅ Added expense:\n"
            f"Item: {item}\n"
            f"Amount: {amount}\n"
            f"Payment Type: {payment_type}"
        )
    except Exception as e:
        # Send error message back to user
        await update.message.reply_text(
            "⚠️ Couldn't add expense:\n"
            f"{e}"
        )


# ================== MAIN BOT LOOP ==================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # /start command
    app.add_handler(CommandHandler("start", start))

    # Any text message (except commands) is treated as an expense
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
