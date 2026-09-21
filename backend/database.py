from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.auth import Auth
from models.user import User
from models.adminAuth import Admin
from models.admindb import Admindb
from models.admindball import Admindball
from models.admindbemp import Admindbemp
from models.sound import Sounds
from models.meet import Meet
from models.queue import Queue

from config import settings

async def init_db():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    if not hasattr(client.__class__, "append_metadata"):
        client.__class__.append_metadata = lambda *args, **kwargs: None
    db = client["gc25"]
    await init_beanie(database=db, document_models=[Auth, User, Admin, Admindb, Admindball, Admindbemp, Sounds, Meet, Queue])
