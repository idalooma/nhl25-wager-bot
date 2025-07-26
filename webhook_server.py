from flask import Flask, render_template, request, abort
import db

app = Flask(__name__)

# ...existing routes...

# Route to display match stats in a beautiful HTML table
@app.route('/show_stats/<int:club_id>/<int:match_number>')
def show_stats(club_id, match_number):
    # Fetch match and stats from db or EA API (mocked here)
    # You should replace this with your actual data fetching logic
    # Example data structure:
    team1_name = "Team Alpha"
    team2_name = "Team Bravo"
    team_stats = [
        ("Goals", 3, 2),
        ("Shots", 15, 12),
        ("Hits", 8, 10),
        ("Faceoffs", 12, 14),
        ("PIM", 4, 6),
        ("Powerplay Goals", 1, 0),
        ("Shorthanded Goals", 0, 0),
    ]
    team1_players = [
        ("123456", "C", 2, 1, 3, 1, 0, 5, 2, 8, 0, 1, 0, 0, 0, "-")
    ]
    team2_players = [
        ("654321", "LW", 1, 0, 1, -1, 2, 3, 4, 2, 0, 0, 0, 0, 0, "-")
    ]
    # TODO: Replace above with real data lookup using club_id and match_number
    return render_template(
        "show_stats.html",
        match_number=match_number,
        team1_name=team1_name,
        team2_name=team2_name,
        team_stats=team_stats,
        team1_players=team1_players,
        team2_players=team2_players
    )

# ...existing code...
import os
from flask import Flask, request, jsonify, render_template_string, render_template, redirect, url_for, session
from db import db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")  # Change this in production!


# Home page
import random
@app.route('/')
def home():
    # Example FAQ and testimonies (could be moved to DB or config)
    faqs = [
        {"q": "What is PUB Stomp Elite?", "a": "PUB Stomp Elite is a Discord-integrated platform for NHL25 wager matches, stats, and community events."},
        {"q": "How do I join a wager match?", "a": "Join our Discord, use the bot to create or join a lobby, and follow the instructions."},
        {"q": "Is my money safe?", "a": "All payments are handled securely via PayPal and all matches are logged for transparency."},
        {"q": "How do payouts work?", "a": "Winners are paid out instantly to their PayPal account after match verification."},
        {"q": "Can I see my stats?", "a": "Yes! Use the bot or website to view your stats and match history."}
    ]
    testimonies = [
        "Best NHL wager experience I've had! - @HockeyFan#1234",
        "Super easy to use and payouts are fast. - @SniperKing#5678",
        "Love the stats dashboard and Discord integration! - @GoaliePro#9999",
        "Great community and fair matches. - @IceBreaker#1111",
        "I won my first match and got paid instantly! - @Rookie#2222"
    ]
    random_testimony = random.choice(testimonies)
    return render_template('index.html', faqs=faqs, random_testimony=random_testimony)

# Lobbies history page
@app.route('/lobbies')
def lobbies():
    from db import db
    with db.get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM lobbies ORDER BY created_at DESC")
        lobbies = c.fetchall()
    return render_template('lobbies.html', lobbies=lobbies)

# Simple admin password (change in production!)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "nhl25admin")
# PayPal webhook endpoint for payment and billing agreement confirmation

# =========================
# ADMIN DASHBOARD ROUTES
# =========================

# Login page
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid password."
    return render_template('admin_login.html', error=error)

# Logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    # Fetch all data
    with db.get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = c.fetchall()
        c.execute('SELECT * FROM lobbies')
        lobbies = c.fetchall()
        c.execute('SELECT * FROM transactions')
        transactions = c.fetchall()
        c.execute('SELECT * FROM stats')
        stats = c.fetchall()
    # Get pending withdrawals
    pending_withdrawals = db.get_pending_withdrawals()
    return render_template('admin.html', users=users, lobbies=lobbies, transactions=transactions, stats=stats, pending_withdrawals=pending_withdrawals)
# Mark withdrawal as paid and debit user wallet
@app.route('/admin/withdrawal/<int:withdrawal_id>/mark_paid', methods=['POST'])
def admin_mark_withdrawal_paid(withdrawal_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    withdrawal = db.get_withdrawal_by_id(withdrawal_id)
    if not withdrawal:
        abort(404)
    user_id = withdrawal[1]
    discord_id = withdrawal[2]
    amount_cents = withdrawal[4]
    # Debit wallet and add transaction
    db.update_wallet(discord_id, -amount_cents)
    db.add_transaction(user_id, "withdrawal", -amount_cents, None)
    db.mark_withdrawal_paid(withdrawal_id)
    return redirect(url_for('admin_dashboard'))

# Edit user
@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    with db.get_db() as conn:
        c = conn.cursor()
        if request.method == 'POST':
            username = request.form.get('username')
            wallet_cents = request.form.get('wallet_cents')
            paypal_agreement_id = request.form.get('paypal_agreement_id')
            c.execute('UPDATE users SET username=?, wallet_cents=?, paypal_agreement_id=? WHERE id=?',
                      (username, wallet_cents, paypal_agreement_id, user_id))
            conn.commit()
            return redirect(url_for('admin_dashboard'))
        c.execute('SELECT * FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
    return render_template('admin_edit_user.html', user=user)

# Delete user
@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
def admin_delete_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    with db.get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

# Clear all data
@app.route('/admin/clear', methods=['POST'])
def admin_clear_all_data():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db.clear_all_data()
    return redirect(url_for('admin_dashboard'))

# Minimal HTML templates (can be moved to separate files if needed)
ADMIN_LOGIN_TEMPLATE = '''
<html><head><title>Admin Login</title></head><body>
<h2>Admin Login</h2>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post">
    <input type="password" name="password" placeholder="Password" required />
    <input type="submit" value="Login" />
</form>
</body></html>
'''

# Documentation page
@app.route('/docs')
def docs():
    return render_template('docs.html')

# Payment success page
@app.route('/success')
def payment_success():
    return render_template('success.html')


# Payment cancel page
@app.route('/cancel')
def payment_cancel():
    return render_template('cancel.html')

# PayPal webhook endpoint for payment and billing agreement confirmation
@app.route("/paypal_webhook", methods=["POST"])
def paypal_webhook():
    try:
        data = request.json
        print("[WEBHOOK] Received data:", data)
        event_type = data.get("event_type")
        print("[WEBHOOK] Event type:", event_type)
        resource = data.get("resource", {})


        # Handle completed payment (sandbox/test event)
        if event_type == "PAYMENTS.PAYMENT.CREATED":
            print("[WEBHOOK] Handling PAYMENTS.PAYMENT.CREATED")
            # Discord ID is in the transaction description or item SKU
            transactions = resource.get('transactions', [])
            if transactions:
                description = transactions[0].get('description', '')
                items = transactions[0].get('item_list', {}).get('items', [])
                discord_id = None
                if items and 'sku' in items[0]:
                    discord_id = items[0]['sku']
                elif 'Discord user' in description:
                    # Extract Discord ID from description
                    import re
                    m = re.search(r'Discord user (\d+)', description)
                    if m:
                        discord_id = m.group(1)
                amount = transactions[0].get('amount', {})
                amount_cents = int(float(amount.get('total', '0')) * 100)
                print(f"[WEBHOOK] Discord ID: {discord_id}, Amount: {amount_cents}")
                if discord_id and amount_cents > 0:
                    db.update_wallet(discord_id, amount_cents)
                    user = db.get_user(discord_id)
                    if user:
                        db.add_transaction(user[0], "deposit", amount_cents, None)
                    return jsonify(success=True), 200
                else:
                    print("[WEBHOOK] Missing discord_id or amount")
                    return jsonify(error="Missing discord_id or amount"), 400
            else:
                print("[WEBHOOK] No transactions found in resource")
                return jsonify(error="No transactions found"), 400

        # Handle completed payment (live event)
        if event_type == "PAYMENT.SALE.COMPLETED":
            print("[WEBHOOK] Handling PAYMENT.SALE.COMPLETED")
            discord_id = resource.get("custom")
            amount = resource.get("amount", {})
            print("[WEBHOOK] Resource:", resource)
            print("[WEBHOOK] Discord ID:", discord_id, "Amount:", amount)
            amount_cents = int(float(amount.get("total", "0")) * 100)
            if discord_id and amount_cents > 0:
                db.update_wallet(discord_id, amount_cents)
                user = db.get_user(discord_id)
                if user:
                    db.add_transaction(user[0], "deposit", amount_cents, None)
                return jsonify(success=True), 200
            else:
                print("[WEBHOOK] Missing discord_id or amount")
                return jsonify(error="Missing discord_id or amount"), 400

        # Handle billing agreement creation
        if event_type == "BILLING.SUBSCRIPTION.CREATED":
            print("[WEBHOOK] Handling BILLING.SUBSCRIPTION.CREATED")
            discord_id = resource.get("custom")
            agreement_id = resource.get("id")
            print("[WEBHOOK] Discord ID:", discord_id, "Agreement ID:", agreement_id)
            if discord_id and agreement_id:
                # Store agreement_id in users table
                with db.get_db() as conn:
                    c = conn.cursor()
                    c.execute("UPDATE users SET paypal_agreement_id = ? WHERE discord_id = ?", (agreement_id, discord_id))
                    conn.commit()
                return jsonify(success=True), 200
            else:
                print("[WEBHOOK] Missing discord_id or agreement_id")
                return jsonify(error="Missing discord_id or agreement_id"), 400

        # Handle payout batch processing
        if event_type == "PAYMENT.PAYOUTSBATCH.PROCESSING":
            print("[WEBHOOK] Payout batch is processing.")
            return jsonify(success=True), 200

        # Handle payout batch success
        if event_type == "PAYMENT.PAYOUTSBATCH.SUCCESS":
            print("[WEBHOOK] Payout batch completed successfully.")
            return jsonify(success=True), 200

        # Handle payout item unclaimed (recipient has not accepted payout)
        if event_type == "PAYMENT.PAYOUTS-ITEM.UNCLAIMED":
            print("[WEBHOOK] Payout item is unclaimed.")
            payout_item = resource.get('payout_item', {})
            receiver = payout_item.get('receiver')
            amount = payout_item.get('amount', {})
            value = amount.get('value')
            currency = amount.get('currency')
            print(f"[WEBHOOK] Unclaimed payout to {receiver} for {value} {currency}")
            # Optionally: Find user by PayPal email and refund wallet here
            # Example (uncomment to enable automatic refund):
            # with db.get_db() as conn:
            #     c = conn.cursor()
            #     c.execute("SELECT id, discord_id FROM users WHERE paypal_email = ?", (receiver,))
            #     user = c.fetchone()
            #     if user:
            #         refund_cents = int(float(value) * 100)
            #         c.execute("UPDATE users SET wallet_cents = wallet_cents + ? WHERE id = ?", (refund_cents, user[0]))
            #         conn.commit()
            return jsonify(success=True), 200

        print("[WEBHOOK] Event not handled or unknown event type.")
        return jsonify(success=True), 200
    except Exception as e:
        print("[WEBHOOK] Exception:", str(e))
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 1000)), debug=True)