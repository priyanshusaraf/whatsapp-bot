# scheduler/scheduler_service.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
from pytz import timezone
# Initialize Logger
logger = logging.getLogger(__name__)

# Configure Redis Job Store
jobstores = {
    "default": RedisJobStore(
        host="localhost",
        port=6379,
        db=0,
    )
}

# Configure APScheduler Executors
executors = {
    "default": ThreadPoolExecutor(10),
}

# Initialize and Start the Scheduler
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, timezone=timezone("Asia/Kolkata"), job_defaults={"coalesce": False, "max_instances": 1},)
scheduler.start()

logger.info("APScheduler initialized with Redis-backed job store.")
