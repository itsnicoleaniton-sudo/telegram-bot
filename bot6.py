import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- Config ----------------
BOT_TOKEN = "7998864648:AAGMXJTpZbgjIHCefV-dcsqdNtPsgQTvqi4"  # <-- Put your bot token here
ADMIN_IDS = [6135858892]  # <-- Replace with your Telegram ID for admin
SUPPORT_CONTACT = "@openw1ndows"

CRYPTO_WALLETS = {
    "btc": "bc1qknssp6tmvw0u27cftqzvwsew3gcqke4h03gxqm",
    "eth": "0x9C23535e442f5297259D330dDFb786c6C6c6711C",
    "usdt_trc20": "TP23gd4u7yw8doTYhKGyPsDb43QyyeeLLg"
}

PRODUCTS = {
    "otp_grabber": 20,
    "lookup": 10,
    "email_bomber": 10
}

# ---------------- Data File Setup ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "users.json")

# ---------------- Data Handling ----------------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- Crypto Price Fetch ----------------
def get_crypto_amount(usd_amount, crypto="btc"):
    if crypto == "usdt_trc20":
        return usd_amount  # USDT is 1:1
    crypto_id = {"btc": "bitcoin", "eth": "ethereum"}.get(crypto)
    if not crypto_id:
        return None
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
        response = requests.get(url).json()
        price = response[crypto_id]["usd"]
        return round(usd_amount / price, 6)
    except:
        return None

# ---------------- Menus ----------------
async def show_main_menu(update_or_query):
    keyboard = [
        [InlineKeyboardButton("📦 Products", callback_data="products")],
        [InlineKeyboardButton("💳 Buy", callback_data="buy_menu")],
        [InlineKeyboardButton("💰 Deposit Funds", callback_data="deposit")],
        [InlineKeyboardButton("💳 Balance", callback_data="balance")],
        [InlineKeyboardButton("🛠 Support", callback_data="support")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- Command Handlers ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"balance": 0, "pending_deposit": None, "purchases": []}
        save_data(data)
    await show_main_menu(update)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Commands:\n/start - main menu\n/help - this message\n/balance - check your balance"
    await update.message.reply_text(text)

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    data.setdefault(user_id, {"balance": 0, "pending_deposit": None, "purchases": []})
    balance = data[user_id]["balance"]
    pending = data[user_id].get("pending_deposit")
    text = f"💳 Your current balance: ${balance}\n"
    if pending:
        amount = pending.get("amount_usd")
        wallet = pending.get("wallet")
        wallet_text = wallet.upper() if wallet else "Not chosen"
        text += f"⏳ Pending deposit: ${amount} via {wallet_text}"
    else:
        text += "⏳ No pending deposits"
    await update.message.reply_text(text)

# ---------------- Admin Notification ----------------
async def notify_admin(user_id: str, amount: int, wallet: str, context: ContextTypes.DEFAULT_TYPE):
    for admin_id in ADMIN_IDS:
        keyboard = [
            [InlineKeyboardButton(f"✅ Confirm ${amount} deposit from user {user_id}", callback_data=f"confirm:{user_id}")]
        ]
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"User {user_id} made a deposit of ${amount} via {wallet.upper()}.\nPress confirm when received:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ---------------- Callback Handler ----------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()
    data.setdefault(user_id, {"balance": 0, "pending_deposit": None, "purchases": []})

    # ---------- Main Menu ----------
    if query.data == "main_menu":
        await show_main_menu(query)

    # ---------- Products ----------
    elif query.data == "products":
        text = "Available products:\n\n"
        for k, p in PRODUCTS.items():
            text += f"{k} — ${p}\n"
        keyboard = [[InlineKeyboardButton("Back", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # ---------- Buy ----------
    elif query.data == "buy_menu":
        balance = data[user_id]["balance"]
        keyboard = [[InlineKeyboardButton(f"{k} - ${p}", callback_data=f"buy:{k}")] for k, p in PRODUCTS.items()]
        keyboard.append([InlineKeyboardButton("Back", callback_data="main_menu")])
        await query.edit_message_text(f"💳 Your balance: ${balance}\nChoose a product to buy:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("buy:"):
        product_key = query.data.split(":")[1]
        price = PRODUCTS.get(product_key)
        balance = data[user_id]["balance"]
        if balance < price:
            keyboard = [[InlineKeyboardButton("Back", callback_data="buy_menu")]]
            await query.edit_message_text(f"❌ Insufficient balance (${balance}). Please deposit funds first.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            data[user_id]["balance"] -= price
            data[user_id]["purchases"].append(product_key)
            save_data(data)
            keyboard = [[InlineKeyboardButton("Back", callback_data="main_menu")]]
            await query.edit_message_text(f"✅ Purchase successful! You bought {product_key} for ${price}.", reply_markup=InlineKeyboardMarkup(keyboard))

    # ---------- Deposit ----------
    elif query.data == "deposit":
        keyboard = [
            [InlineKeyboardButton("$50", callback_data="dep_50"),
             InlineKeyboardButton("$100", callback_data="dep_100")],
            [InlineKeyboardButton("$300", callback_data="dep_300"),
             InlineKeyboardButton("$500", callback_data="dep_500")],
            [InlineKeyboardButton("Back", callback_data="main_menu")]
        ]
        await query.edit_message_text("💰 Choose the amount to deposit:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("dep_") and "wallet" not in query.data:
        amount_usd = int(query.data.split("_")[1])
        data[user_id]["pending_deposit"] = {"amount_usd": amount_usd, "wallet": None}
        save_data(data)

        btc_eq = get_crypto_amount(amount_usd, "btc")
        eth_eq = get_crypto_amount(amount_usd, "eth")
        usdt_eq = get_crypto_amount(amount_usd, "usdt_trc20")

        crypto_display = f"""💰 You chose ${amount_usd}.
Equivalent amounts:
- BTC: {btc_eq} BTC
- ETH: {eth_eq} ETH
- USDT TRC20: {usdt_eq} USDT
Now select your crypto method:"""

        keyboard = [
            [InlineKeyboardButton("BTC", callback_data="dep_wallet_btc"),
             InlineKeyboardButton("ETH", callback_data="dep_wallet_eth"),
             InlineKeyboardButton("USDT TRC20", callback_data="dep_wallet_usdt_trc20")],
            [InlineKeyboardButton("Back", callback_data="deposit")]
        ]
        await query.edit_message_text(crypto_display, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("dep_wallet_"):
        wallet_type = query.data.split("_")[2]
        wallet_address = CRYPTO_WALLETS.get(wallet_type, "Not available")
        amount_usd = data[user_id]["pending_deposit"]["amount_usd"]
        data[user_id]["pending_deposit"]["wallet"] = wallet_type
        save_data(data)
        keyboard = [[InlineKeyboardButton("Back", callback_data="deposit")]]
        await query.edit_message_text(
            f"💰 Send ${amount_usd} to this address:\n`{wallet_address}`\n⏳ Waiting for deposit...",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await notify_admin(user_id, amount_usd, wallet_type, context)

    # ---------- Admin Confirm ----------
    elif query.data.startswith("confirm:"):
        admin_id = update.effective_user.id
        if admin_id not in ADMIN_IDS:
            await query.answer("❌ Not authorized.", show_alert=True)
            return
        target_user_id = query.data.split(":")[1]
        if target_user_id not in data or not data[target_user_id].get("pending_deposit"):
            await query.answer("❌ No pending deposit found.", show_alert=True)
            return
        amount = data[target_user_id]["pending_deposit"]["amount_usd"]
        data[target_user_id]["balance"] += amount
        data[target_user_id]["pending_deposit"] = None
        save_data(data)
        await query.edit_message_text(f"✅ Deposit of ${amount} for user {target_user_id} confirmed!")
        try:
            await context.bot.send_message(target_user_id, f"✅ Your deposit of ${amount} has been confirmed!")
        except:
            pass

    # ---------- Help ----------
    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("Back", callback_data="main_menu")]]
        await query.edit_message_text("Use the menu to navigate.", reply_markup=InlineKeyboardMarkup(keyboard))

    # ---------- Support ----------
    elif query.data == "support":
        keyboard = [[InlineKeyboardButton("Back", callback_data="main_menu")]]
        await query.edit_message_text(f"🛠 Support: {SUPPORT_CONTACT}", reply_markup=InlineKeyboardMarkup(keyboard))

    # ---------- Balance ----------
    elif query.data == "balance":
        balance = data[user_id]["balance"]
        pending = data[user_id].get("pending_deposit")
        text = f"💳 Your current balance: ${balance}\n"
        if pending:
            amount = pending.get("amount_usd")
            wallet = pending.get("wallet")
            wallet_text = wallet.upper() if wallet else "Not chosen"
            text += f"⏳ Pending deposit: ${amount} via {wallet_text}"
        else:
            text += "⏳ No pending deposits"
        keyboard = [[InlineKeyboardButton("Back", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- Main ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
