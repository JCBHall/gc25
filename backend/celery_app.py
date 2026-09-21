from celery import Celery
from celery.schedules import crontab
from config import settings

app = Celery('backend',
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
            include=['tasks'])

app.conf.timezone = "Asia/Kolkata"
app.conf.enable_utc = False

app.conf.update(
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "run-daily-11pm": {
        "task": "tasks.EODTask",
        "schedule": crontab(hour=23, minute=59),
    },
    "send-mails": {
        "task": "tasks.sendMailFromQueue",
        "schedule": crontab(hour=10, minute=00),
    },
    "analyze-emps":{
        "task": "tasks.analyseEmps",
        "schedule": crontab(hour=23, minute=59)
    }
}

if __name__ == '__main__':
    app.start()

