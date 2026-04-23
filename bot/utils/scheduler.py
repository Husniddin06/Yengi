import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.database import db

logger = logging.getLogger(__name__)

def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    async def daily_reset():
        # Har kuni 5 tanga ayirish va rasm limitini 3 ga yangilash
        await db.daily_coin_deduction()
        logger.info("Daily coin deduction and image limit reset completed.")
        
    scheduler.add_job(daily_reset, CronTrigger(hour=0, minute=0))
    
    scheduler.start()
    return scheduler
