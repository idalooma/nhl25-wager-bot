
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
        success_url = "https://actually-deep-salmon.ngrok-free.app/success"
        cancel_url = "https://actually-deep-salmon.ngrok-free.app/cancel"
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
        success_url = "https://actually-deep-salmon.ngrok-free.app/paypal_agreement_success"
        cancel_url = "https://actually-deep-salmon.ngrok-free.app/paypal_agreement_cancel"
        approval_url, plan_id = create_billing_agreement_approval_url(discord_id, plan_name, amount_cents, success_url, cancel_url)
        await interaction.response.send_message(f"To save your PayPal info for future payments, please authorize here: {approval_url}\nAfter approval, your info will be saved for future deposits.")

    @app_commands.command(name="withdraw", description="Withdraw money from your wallet.")
    async def withdraw(self, interaction: discord.Interaction, amount: float, paypal_email: str = None):
        discord_id = str(interaction.user.id)
        user = db.get_user(discord_id)
        if not user:
            await interaction.response.send_message("You need to deposit first.")
            return
        wallet_cents = user[3]
        withdraw_cents = int(amount * 100)
        if wallet_cents < withdraw_cents:
            await interaction.response.send_message("Insufficient balance.")
            return
        # Get or update PayPal email
        if not paypal_email:
            # Try to get from DB
            paypal_email_db = None
            if len(user) > 5:
                paypal_email_db = user[5]
            if not paypal_email_db:
                await interaction.response.send_message("Please provide your PayPal email for payout: `/withdraw [amount] [paypal_email]`")
                return
            paypal_email = paypal_email_db
        # Try payout
        try:
            payout_id = send_paypal_payout(paypal_email, withdraw_cents)
            db.update_wallet(discord_id, -withdraw_cents)
            db.add_transaction(user[0], "withdrawal", -withdraw_cents, None)
            db.update_paypal_email(discord_id, paypal_email)
            await interaction.response.send_message(f"Withdrawal of ${amount:.2f} sent to {paypal_email}. Payout batch: {payout_id}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Withdrawal failed: {str(e)}")

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
