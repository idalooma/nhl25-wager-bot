def get_active_lobbies():
    """
    Return all lobbies with status 'open' or 'started'.
    """
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM lobbies WHERE status IN ('open', 'started') ORDER BY created_at DESC")
        return c.fetchall()
def get_stats(user_id):
    """
    Get a user's stats row from the stats table.
    """
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
        return c.fetchone()
def update_stats(user_id, games_played=0, wins=0, losses=0, goals=0, assists=0):
    """
    Incrementally update a user's stats in the stats table.
    """
    with get_db() as conn:
        c = conn.cursor()
        # If no stats row exists, insert one
        c.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            c.execute(
                "INSERT INTO stats (user_id, games_played, wins, losses, goals, assists) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, games_played, wins, losses, goals, assists)
            )
        else:
            c.execute(
                "UPDATE stats SET games_played = games_played + ?, wins = wins + ?, losses = losses + ?, goals = goals + ?, assists = assists + ? WHERE user_id = ?",
                (games_played, wins, losses, goals, assists, user_id)
            )
        conn.commit()
import sqlite3

DB_PATH = "nhl25bot.db"

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_db() as conn, open("db/schema.sql") as f:
        conn.executescript(f.read())

def add_user(discord_id, username, paypal_email=None):
    with get_db() as conn:
        c = conn.cursor()
        # Try to insert, or update username/paypal_email if user exists
        c.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,))
        row = c.fetchone()
        if row:
            if paypal_email:
                c.execute("UPDATE users SET username = ?, paypal_email = ? WHERE discord_id = ?", (username, paypal_email, discord_id))
            else:
                c.execute("UPDATE users SET username = ? WHERE discord_id = ?", (username, discord_id))
        else:
            if paypal_email:
                c.execute("INSERT INTO users (discord_id, username, paypal_email) VALUES (?, ?, ?)", (discord_id, username, paypal_email))
            else:
                c.execute("INSERT INTO users (discord_id, username) VALUES (?, ?)", (discord_id, username))
        conn.commit()

def get_user(discord_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
        return c.fetchone()

def update_paypal_email(discord_id, paypal_email):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET paypal_email = ? WHERE discord_id = ?", (paypal_email, discord_id))
        conn.commit()
def update_wallet(discord_id, delta):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET wallet_cents = wallet_cents + ? WHERE discord_id = ?", (delta, discord_id))
        conn.commit()

def create_lobby(code, creator_id, wager_cents, club_id=None):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO lobbies (code, creator_id, wager_cents, team1, team2, club_id) VALUES (?, ?, ?, ?, ?, ?)",
            (code, creator_id, wager_cents, "", "", club_id)
        )
        conn.commit()

def get_lobby_by_code(code):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM lobbies WHERE code = ?", (code,))
        return c.fetchone()

def update_lobby_teams(code, team1=None, team2=None):
    with get_db() as conn:
        c = conn.cursor()
        if team1 is not None:
            c.execute("UPDATE lobbies SET team1 = ? WHERE code = ?", (team1, code))
        if team2 is not None:
            c.execute("UPDATE lobbies SET team2 = ? WHERE code = ?", (team2, code))
        conn.commit()

def update_lobby_status(code, status, start_time=None):
    with get_db() as conn:
        c = conn.cursor()
        if start_time is not None:
            c.execute("UPDATE lobbies SET status = ?, start_time = ? WHERE code = ?", (status, start_time, code))
        else:
            c.execute("UPDATE lobbies SET status = ? WHERE code = ?", (status, code))
        conn.commit()


def add_transaction(user_id, tx_type, amount_cents, lobby_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO transactions (user_id, type, amount_cents, lobby_id) VALUES (?, ?, ?, ?)",
            (user_id, tx_type, amount_cents, lobby_id)
        )
        conn.commit()

def clear_all_data():
    """
    Delete all data from all tables in the database. Use with caution!
    """
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM transactions")
        c.execute("DELETE FROM stats")
        c.execute("DELETE FROM lobbies")
        c.execute("DELETE FROM users")
        conn.commit()

# Withdrawal queue logic
def add_withdrawal(user_id, discord_id, email, amount_cents):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO withdrawals (user_id, discord_id, email, amount_cents, status) VALUES (?, ?, ?, ?, 'pending')", (user_id, discord_id, email, amount_cents))
        conn.commit()

def get_pending_withdrawals():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY requested_at ASC")
        return c.fetchall()

def mark_withdrawal_paid(withdrawal_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE withdrawals SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?", (withdrawal_id,))
        conn.commit()

def get_withdrawal_by_id(withdrawal_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        return c.fetchone()