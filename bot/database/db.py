import aiosqlite
import datetime

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
                language_code TEXT DEFAULT 'en',
                is_blocked BOOLEAN DEFAULT FALSE
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

async def init_extras():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id INTEGER PRIMARY KEY,
                last_claimed TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                premium_days INTEGER DEFAULT 0,
                extra_requests INTEGER DEFAULT 0,
                uses_left INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                user_id INTEGER,
                code TEXT,
                redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, code)
            )
        ''')
        await db.commit()

# --- User Functions ---
async def add_user(user_id, username, first_name, last_name, language_code, referred_by=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (id, username, first_name, last_name, language_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language_code, referred_by))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def set_user_language(user_id, lang_code):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET language_code = ? WHERE id = ?', (lang_code, user_id))
        await db.commit()

async def update_user_premium(user_id, is_premium, premium_until):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET is_premium = ?, premium_until = ? WHERE id = ?', 
                         (is_premium, premium_until, user_id))
        await db.commit()

async def decrement_daily_limit(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET daily_limit = daily_limit - 1 WHERE id = ? AND daily_limit > 0', (user_id,))
        await db.commit()

async def block_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET is_blocked = 1 WHERE id = ?', (user_id,))
        await db.commit()

async def unblock_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET is_blocked = 0 WHERE id = ?', (user_id,))
        await db.commit()

# --- Referral Functions ---
async def add_referral(referrer_id, referred_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
        await db.commit()

async def increment_referrals_count(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE id = ?', (user_id,))
        await db.commit()

# --- Payment Functions ---
async def add_payment(user_id, amount, period):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO payments (user_id, amount, status, period)
            VALUES (?, ?, 'pending', ?)
        ''', (user_id, amount, period))
        payment_id = cursor.lastrowid
        await db.commit()
        return payment_id

async def get_payment(payment_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_payment_status(payment_id, status, approved_by=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE payments SET status = ?, approved_by = ? WHERE id = ?', (status, approved_by, payment_id))
        await db.commit()

async def get_pending_payments():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE status = 'pending'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# --- Conversation Functions ---
async def add_chat_history(user_id, user_message, bot_message):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)', (user_id, 'user', user_message))
        await db.execute('INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)', (user_id, 'assistant', bot_message))
        await db.commit()

async def get_chat_history(user_id, limit=10):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit*2)) as cursor:
            rows = await cursor.fetchall()
            history = []
            for row in reversed(rows):
                history.append({"role": row["role"], "content": row["content"]})
            return history

async def clear_conversation_history(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
        await db.commit()

# --- Admin Stats ---
async def get_total_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            row = await cursor.fetchone()
            return row[0]

async def get_premium_users_count():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1') as cursor:
            row = await cursor.fetchone()
            return row[0]

async def get_all_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# --- Scheduler Functions ---
async def reset_all_daily_limits(limit):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('UPDATE users SET daily_limit = ? WHERE is_premium = 0', (limit,))
        await db.commit()
        return cursor.rowcount

async def expire_premium_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        now = datetime.datetime.now()
        cursor = await db.execute('UPDATE users SET is_premium = 0 WHERE is_premium = 1 AND premium_until < ?', (now,))
        await db.commit()
        return cursor.rowcount

async def trim_conversations_per_user(keep=100):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            DELETE FROM conversations 
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) as rn
                    FROM conversations
                ) WHERE rn <= ?
            )
        ''', (keep,))
        await db.commit()
        return 0

# --- Bonus & Promo Functions ---
async def claim_daily_bonus(user_id, bonus_amount):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        today = datetime.date.today().isoformat()
        async with db.execute('SELECT last_claimed FROM daily_bonus WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == today:
                return False
            
            await db.execute('INSERT OR REPLACE INTO daily_bonus (user_id, last_claimed) VALUES (?, ?)', (user_id, today))
            await db.execute('UPDATE users SET daily_limit = daily_limit + ? WHERE id = ?', (bonus_amount, user_id))
            await db.commit()
            return True

async def create_promo(code, days, reqs, uses):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            INSERT INTO promo_codes (code, premium_days, extra_requests, uses_left)
            VALUES (?, ?, ?, ?)
        ''', (code.upper(), days, reqs, uses))
        await db.commit()

async def redeem_promo(user_id, code):
    code = code.upper()
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM promo_codes WHERE code = ? AND uses_left > 0', (code,)) as cursor:
            promo = await cursor.fetchone()
            if not promo:
                return None
            
        async with db.execute('SELECT 1 FROM promo_redemptions WHERE user_id = ? AND code = ?', (user_id, code)) as cursor:
            if await cursor.fetchone():
                return "already"
            
        if promo["premium_days"] > 0:
            user = await get_user(user_id)
            current_until = user["premium_until"]
            if current_until:
                try:
                    start_dt = datetime.datetime.strptime(str(current_until), "%Y-%m-%d %H:%M:%S.%f")
                    if start_dt < datetime.datetime.now():
                        start_dt = datetime.datetime.now()
                except ValueError:
                    start_dt = datetime.datetime.now()
            else:
                start_dt = datetime.datetime.now()
            
            new_until = start_dt + datetime.timedelta(days=promo["premium_days"])
            await db.execute('UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?', (new_until, user_id))
            
        if promo["extra_requests"] > 0:
            await db.execute('UPDATE users SET daily_limit = daily_limit + ? WHERE id = ?', (promo["extra_requests"], user_id))
            
        await db.execute('INSERT INTO promo_redemptions (user_id, code) VALUES (?, ?)', (user_id, code))
        await db.execute('UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?', (code,))
        await db.commit()
        return {"premium_days": promo["premium_days"], "extra_requests": promo["extra_requests"]}
