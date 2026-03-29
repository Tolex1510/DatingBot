from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "dating_bot",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "hourly-behavioral-rating-update": {
            "task": "app.workers.tasks.hourly_rating_update",
            "schedule": crontab(minute=0),  # every hour
        },
        "daily-full-rating-update": {
            "task": "app.workers.tasks.daily_rating_update",
            "schedule": crontab(hour=3, minute=0),  # daily at 3:00 AM
        },
        "weekly-rating-aggregation": {
            "task": "app.workers.tasks.weekly_rating_aggregation",
            "schedule": crontab(day_of_week=0, hour=4, minute=0),  # Sunday 4:00 AM
        },
    },
)
