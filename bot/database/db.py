
import aiosqlite
import datetime
import json

DATABASE_NAME = 'smartai_bot.db'

async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until DATETIME,
                daily_limit INTEGER DEFAULT 10,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                language_code TEXT DEFAULT 'en'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT,
                status TEXT,
                period TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(id),
                FOREIGN KEY (referred_id) REFERENCES users(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        await db.commit()

async def add_user(user_id, username, first_name, last_name, language_code, referred_by=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name, last_name, language_code, referred_by) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, first_name, last_name, language_code, referred_by)
        )
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def update_user_premium(user_id, is_premium, premium_until):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET is_premium = ?, premium_until = ? WHERE id = ?",
            (is_premium, premium_until, user_id)
        )
        await db.commit()

async def update_user_daily_limit(user_id, new_limit):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET daily_limit = ? WHERE id = ?",
            (new_limit, user_id)
        )
        await db.commit()

async def increment_referrals_count(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET referrals_count = referrals_count + 1 WHERE id = ?",
            (user_id,)
        )
        await db.commit()

async def add_payment(user_id, amount, currency, status, period):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, amount, currency, status, period) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, currency, status, period)
        )
        await db.commit()
        return cursor.lastrowid

async def update_payment_status(payment_id, status, approved_by=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE payments SET status = ?, approved_by = ? WHERE id = ?",
            (status, approved_by, payment_id)
        )
        await db.commit()

async def get_pending_payments():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payments WHERE status = 'pending'")
        payments = await cursor.fetchall()
        return [dict(p) for p in payments]

async def add_referral(referrer_id, referred_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
            (referrer_id, referred_id)
        )
        await db.commit()

async def get_referrals_by_referrer(referrer_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM referrals WHERE referrer_id = ?", (referrer_id,))
        referrals = await cursor.fetchall()
        return [dict(r) for r in referrals]

async def get_all_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users")
        users = await cursor.fetchall()
        return [dict(u) for u in users]

async def get_total_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = await cursor.fetchone()
        return count[0]

async def get_premium_users_count():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = TRUE")
        count = await cursor.fetchone()
        return count[0]

async def get_user_by_referred_id(referred_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = (SELECT referrer_id FROM referrals WHERE referred_id = ?)", (referred_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def block_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("UPDATE users SET daily_limit = 0 WHERE id = ?", (user_id,))
        await db.commit()

async def unblock_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("UPDATE users SET daily_limit = 10 WHERE id = ?", (user_id,))
        await db.commit()

async def set_user_premium_status(user_id, is_premium, premium_until=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET is_premium = ?, premium_until = ? WHERE id = ?",
            (is_premium, premium_until, user_id)
        )
        await db.commit()

async def get_user_by_id(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def add_conversation_message(user_id, role, content):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()

async def get_conversation_history(user_id, limit=10):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        history = await cursor.fetchall()
        return [dict(h) for h in reversed(history)]

async def clear_conversation_history(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        await db.commit()
