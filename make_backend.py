import os

# Combine tasks
with open("backend/tasks_update.py", "r", encoding="utf-8") as f:
    update_tasks = f.read()

with open("backend/tasks_scheduler.py", "r", encoding="utf-8") as f:
    scheduler_tasks = f.read()

# Replace `.celery` import with `celery_app`
update_tasks = update_tasks.replace("from .celery import app", "from celery_app import app")
scheduler_tasks = scheduler_tasks.replace("from .celery import app", "")

# Remove duplicate imports and clean up
combined_tasks = update_tasks + "\n\n" + scheduler_tasks
combined_tasks = combined_tasks.replace("from models.queue", "from models.queue")
combined_tasks = combined_tasks.replace("from models.admindbemp", "from models.admindbemp")

with open("backend/tasks.py", "w", encoding="utf-8") as f:
    f.write(combined_tasks)

# Create celery_app.py
celery_content = """from celery import Celery
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
"""
with open("backend/celery_app.py", "w", encoding="utf-8") as f:
    f.write(celery_content)

# Create app.py
app_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db

# Import routers
from routes.auth import auth_router
from routes.admindb import admin_router
from routes.adminAuth import adminAuth_router
from routes.user import user_router
from routes.dashboard import dashboard_router
from routes.chat import chat_router
from routes.reportAll import all_report_router
from routes.reportEmp import emp_report_router

origins = [
    settings.FRONTEND_ORIGIN
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def start_database():
    await init_db()

# Include routes
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(admin_router, prefix="/admindb", tags=["AdminDB"])
app.include_router(adminAuth_router, prefix="/adminAuth", tags=["AdminAuth"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(chat_router, prefix="/ws", tags=["Chat"])
app.include_router(all_report_router, prefix="/reportAll", tags=["ReportAll"])
app.include_router(emp_report_router, prefix="/reportEmp", tags=["ReportEmp"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Unified GC25 API!"}
"""
with open("backend/app.py", "w", encoding="utf-8") as f:
    f.write(app_content)

os.remove("backend/tasks_update.py")
os.remove("backend/tasks_scheduler.py")

