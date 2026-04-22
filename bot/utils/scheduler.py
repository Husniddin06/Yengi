import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db
from config import DEFAULT_DAILY_LIMIT, HISTORY_KEEP

logger = logging.getLogger(__name__)

def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    async def reset_limits():
        n = await db.reset_all_daily_limits(DEFAULT_DAILY_LIMIT)
        logger.info(f"Daily limits reset for {n} users")
        
    async def expire_premium():
        n = await db.expire_premium_users()
        logger.info(f"Expired premium for {n} users")
        
    async def trim_history():
        n = await db.trim_conversations_per_user(keep=HISTORY_KEEP)
        logger.info(f"Trimmed conversation history for {n} users")
        
    scheduler.add_job(reset_limits, CronTrigger(hour=0, minute=0))
    scheduler.add_job(expire_premium, CronTrigger(hour=0, minute=5))
    scheduler.add_job(trim_history, CronTrigger(hour=2, minute=0))
    
    scheduler.start()
    return scheduler
