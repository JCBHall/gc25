from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db

# Import routers
from routes.auth import auth_router
from routes.admindb import admindb_router
from routes.adminAuth import admin_auth_router
from routes.user import user_router
from routes.chat import chat_router
from routes.reportAll import admindball_router
from routes.reportEmp import admindbemp_router

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

from middlewares.auth import AuthMiddleware
from middlewares.adminAuth import AdminAuthMiddleware

app.add_middleware(AuthMiddleware)
app.add_middleware(AdminAuthMiddleware)

@app.on_event("startup")
async def start_database():
    await init_db()

# Include routes
app.include_router(auth_router, prefix="/a/api/v1/emp/auth", tags=["Auth"])
app.include_router(admindb_router, prefix="/a/api/v1/admin/details", tags=["AdminDB"])
app.include_router(admin_auth_router, prefix="/a/api/v1/admin/auth", tags=["AdminAuth"])
app.include_router(user_router, prefix="/a/api/v1/emp/details", tags=["User"])
app.include_router(chat_router, prefix="/ws", tags=["Chat"])
app.include_router(admindball_router, prefix="/r/api/v1/get/report/all", tags=["ReportAll"])
app.include_router(admindbemp_router, prefix="/r/api/v1/get/report", tags=["ReportEmp"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Unified GC25 API!"}

