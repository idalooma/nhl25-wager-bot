
import discord
from discord import app_commands
from discord.ext import commands
from db import db
from payments import create_paypal_payment, create_billing_agreement_approval_url, send_paypal_payout


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="deposit", description="Deposit money into your wallet using PayPal.")
    async def deposit(self, interaction: discord.Interaction, amount: float):
        discord_id = str(interaction.user.id)
        db.add_user(discord_id, interaction.user.name)
        amount_cents = int(amount * 100)
        success_url = "https://actual-panther-gently.ngrok-free.app/success"
        cancel_url = "https://actual-panther-gently.ngrok-free.app/cancel"
        try:
            approval_url = create_paypal_payment(discord_id, amount_cents, success_url, cancel_url)
            await interaction.response.send_message(f"PayPal deposit link: {approval_url}\nAfter payment, your wallet will be credited.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create PayPal payment")

    @app_commands.command(name="save_paypal_info", description="Save your PayPal info for future payments (billing agreement).")
    async def save_paypal_info(self, interaction: discord.Interaction, amount: float):
        discord_id = str(interaction.user.id)
        db.add_user(discord_id, interaction.user.name)
        amount_cents = int(amount * 100)
        plan_name = "NHL25 Wager Billing Agreement"
        success_url = "https://actual-panther-gently.ngrok-free.app/paypal_agreement_success"
        cancel_url = "https://actual-panther-gently.ngrok-free.app/paypal_agreement_cancel"
        approval_url, plan_id = create_billing_agreement_approval_url(discord_id, plan_name, amount_cents, success_url, cancel_url)
        await interaction.response.send_message(f"To save your PayPal info for future payments, please authorize here: {approval_url}\nAfter approval, your info will be saved for future deposits.")

    @app_commands.command(name="withdraw", description="Withdraw money from your wallet.")
    async def withdraw(self, interaction: discord.Interaction, amount: float, paypal_email: str):
        import datetime
        discord_id = str(interaction.user.id)
        user = db.get_user(discord_id)
        if not user:
            await interaction.response.send_message("You need to deposit first.")
            return
        wallet_cents = user[3]
        withdraw_cents = int(amount * 100)
        # Only allow withdrawals in last 7 days of month
        today = datetime.datetime.utcnow().date()
        last_day = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        days_left = (last_day - today).days
        
        if days_left > 7:
            await interaction.response.send_message("Withdrawals are only allowed in the last 7 days of each month.")
            return
        # Only allow if wallet is $500 or more
        if wallet_cents < 50000:
            await interaction.response.send_message("You must have at least $500 in your wallet to withdraw.")
            return
        if withdraw_cents > wallet_cents:
            await interaction.response.send_message("Insufficient balance.")
            return
        if withdraw_cents < 50000:
            await interaction.response.send_message("Minimum withdrawal is $500.")
            return
        # Get or update PayPal email
        if not paypal_email or not paypal_email.strip():
            await interaction.response.send_message("You must provide your PayPal email for payout: `/withdraw [amount] [paypal_email]`")
            return
        # Prevent multiple requests per user per month
        import sqlite3
        import datetime
        now = datetime.datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        conn = sqlite3.connect("nhl25bot.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM withdrawals WHERE discord_id = ? AND requested_at >= ?", (discord_id, month_start.strftime('%Y-%m-%d %H:%M:%S')))
        count = c.fetchone()[0]
        conn.close()
        if count > 0:
            await interaction.response.send_message("You have already requested a withdrawal this month. Please wait until next month.")
            return
        # Queue withdrawal in DB
        db.add_withdrawal(user[0], discord_id, paypal_email, withdraw_cents)
        db.update_paypal_email(discord_id, paypal_email)
        await interaction.response.send_message(f"✅ Payment queued successfully. Admin will process your withdrawal soon.")

    @app_commands.command(name="transactions", description="List your transaction history.")
    async def transactions(self, interaction: discord.Interaction):
        discord_id = str(interaction.user.id)
        user = db.get_user(discord_id)
        if not user:
            await interaction.response.send_message("You have no transaction history.")
            return
        user_id = user[0]
        # Fetch transactions for this user
        import sqlite3
        conn = sqlite3.connect("nhl25bot.db")
        c = conn.cursor()
        c.execute("SELECT type, amount_cents, timestamp, lobby_id FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            await interaction.response.send_message("You have no transaction history.")
            return
        # Format output
        lines = ["**Your Transaction History:**\nType | Amount | Date | Lobby ID"]
        for ttype, amount, ts, lobby_id in rows:
            amt = f"${amount/100:.2f}"
            lobby = str(lobby_id) if lobby_id else "-"
            lines.append(f"{ttype.title()} | {amt} | {ts[:19]} | {lobby}")
        # Discord message limit: 2000 chars
        msg = "\n".join(lines)
        if len(msg) > 1900:
            msg = msg[:1900] + "\n... (truncated)"
        await interaction.response.send_message(msg)


async def setup(bot):
    await bot.add_cog(Money(bot))
