-- SQLite schema for NHL25 Wager Bot

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE NOT NULL,
    username TEXT,
    wallet_cents INTEGER DEFAULT 0,  -- Store amounts in cents for accuracy
    paypal_agreement_id TEXT,        -- Store PayPal billing agreement ID for future payments
    paypal_email TEXT                -- Store PayPal email for payouts
);

CREATE TABLE IF NOT EXISTS lobbies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    creator_id TEXT NOT NULL,
    wager_cents INTEGER NOT NULL,
    team1 TEXT, -- comma-separated Discord IDs
    team2 TEXT,
    status TEXT DEFAULT 'open', -- open, started, completed, cancelled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    club_id INTEGER, -- NHL25 club ID for EA API validation
    start_time INTEGER -- UTC timestamp when game is started
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- deposit, withdrawal, wager, payout
    amount_cents INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    lobby_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    earnings_cents INTEGER DEFAULT 0,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Withdrawal queue for manual payouts
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    discord_id TEXT NOT NULL,
    email TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, paid
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id)
);