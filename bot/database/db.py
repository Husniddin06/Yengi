import aiosqlite
import datetime
import logging

DATABASE_NAME = 'smartai_bot.db'
logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        # Users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until DATETIME,
                coins INTEGER DEFAULT 10,
                daily_image_limit INTEGER DEFAULT 3,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                language_code TEXT DEFAULT 'en',
                is_blocked BOOLEAN DEFAULT FALSE,
                current_character TEXT DEFAULT 'default'
            )
        ''')
        
        # Payments table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Tasks table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT,
                reward INTEGER DEFAULT 5,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # User completed tasks
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_tasks (
                user_id INTEGER,
                task_id INTEGER,
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, task_id)
            )
        ''')
        
        # Conversations table
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
        
        # Daily bonus table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id INTEGER PRIMARY KEY,
                last_claimed TEXT
            )
        ''')
        await db.commit()

async def init_extras():
    pass

# --- User Functions ---
async def add_user(user_id, username, first_name=None, last_name=None, language_code='en', referred_by=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (id, username, first_name, last_name, language_code, referred_by, coins)
            VALUES (?, ?, ?, ?, ?, ?, 10)
        ''', (user_id, username, first_name, last_name, language_code, referred_by))
        if referred_by:
            await db.execute('UPDATE users SET referrals_count = referrals_count + 1, coins = coins + 5 WHERE id = ?', (referred_by,))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_user_language(user_id, language_code):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET language_code = ? WHERE id = ?', (language_code, user_id))
        await db.commit()

async def update_user_coins(user_id, amount):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (amount, user_id))
        await db.commit()

async def update_user_premium(user_id, is_premium, until):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET is_premium = ?, premium_until = ? WHERE id = ?', (is_premium, until, user_id))
        await db.commit()

async def update_user_character(user_id, character):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET current_character = ? WHERE id = ?', (character, user_id))
        await db.commit()

# --- Task Functions ---
async def add_task(title, url, reward=5):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO tasks (title, url, reward) VALUES (?, ?, ?)', (title, url, reward))
        await db.commit()

async def get_active_tasks():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM tasks WHERE is_active = 1') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def complete_task(user_id, task_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT reward FROM tasks WHERE id = ?', (task_id,)) as cursor:
            task = await cursor.fetchone()
            if not task: return False
            reward = task[0]
        
        try:
            await db.execute('INSERT INTO user_tasks (user_id, task_id) VALUES (?, ?)', (user_id, task_id))
            await db.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (reward, user_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

# --- Payment Functions ---
async def add_payment(user_id, amount, method):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('INSERT INTO payments (user_id, amount, method) VALUES (?, ?, ?)', (user_id, amount, method))
        payment_id = cursor.lastrowid
        await db.commit()
        return payment_id

async def get_pending_payments():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT p.*, u.username FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = "pending"') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def approve_payment(payment_id, admin_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)) as cursor:
            payment = await cursor.fetchone()
            if not payment: return False
            user_id = payment['user_id']
            
        await db.execute('UPDATE payments SET status = "approved", approved_by = ? WHERE id = ?', (admin_id, payment_id))
        await db.execute('UPDATE users SET coins = coins + 150, is_premium = 1, premium_until = ? WHERE id = ?', 
                         (datetime.datetime.now() + datetime.timedelta(days=30), user_id))
        await db.commit()
        return user_id

# --- Scheduler Functions ---
async def daily_coin_deduction():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET coins = CASE WHEN coins >= 5 THEN coins - 5 ELSE 0 END')
        await db.execute('UPDATE users SET daily_image_limit = 3')
        await db.commit()

# --- Other Functions ---
async def save_conversation(user_id, user_message, bot_message):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO conversations (user_id, role, content) VALUES (?, "user", ?)', (user_id, user_message))
        await db.execute('INSERT INTO conversations (user_id, role, content) VALUES (?, "assistant", ?)', (user_id, bot_message))
        await db.commit()

async def clear_conversation_history(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
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

async def claim_daily_bonus(user_id, bonus_amount=1):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        today = datetime.date.today().isoformat()
        async with db.execute('SELECT last_claimed FROM daily_bonus WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == today: return False
            await db.execute('INSERT OR REPLACE INTO daily_bonus (user_id, last_claimed) VALUES (?, ?)', (user_id, today))
            await db.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (bonus_amount, user_id))
            await db.commit()
            return True

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

async def get_blocked_users_count():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 1') as cursor:
            row = await cursor.fetchone()
            return row[0]

async def get_all_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
