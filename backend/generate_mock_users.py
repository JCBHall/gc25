import asyncio
import random
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
from datetime import datetime, timedelta
import os

from models.user import User, VibeEntry, TrendEntry, TrendEntryArray, wellnessPointEntry, wellnessPointEntryArray, Reward, Badge
from models.admindb import Admindb
from models.admindball import Admindball
from models.admindbemp import Admindbemp
from models.auth import Auth
from models.adminAuth import Admin
from models.sound import Sounds
from models.meet import Meet
from models.queue import Queue

fake = Faker()

departments = ["Engineering", "Sales", "Marketing", "HR", "Design", "Product"]
roles = ["Associate", "Manager", "Senior Manager", "Director", "VP"]
vibes = ["happy", "tending to happy", "neutral", "sad", "angry"]
avatars = [
    "https://ui-avatars.com/api/?name=John+Doe",
    "https://ui-avatars.com/api/?name=Jane+Smith",
    "https://ui-avatars.com/api/?name=Alex+Johnson",
]

async def generate_users(num_users=1000):
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    if not hasattr(client.__class__, "append_metadata"):
        client.__class__.append_metadata = lambda *args, **kwargs: None
    db = client["gc25"]
    await init_beanie(database=db, document_models=[Auth, User, Admin, Admindb, Admindball, Admindbemp, Sounds, Meet, Queue])

    print("Cleaning up old users and admin DB...")
    await User.delete_all()
    await Admindb.delete_all()
    await Admindball.delete_all()
    await Admindbemp.delete_all()

    print(f"Generating {num_users} users...")
    
    users_to_insert = []
    
    for i in range(num_users):
        empid = f"EMP{str(i+1).zfill(4)}"
        name = fake.name()
        dept = random.choice(departments)
        role = random.choice(roles)
        wellnessScore = random.randint(1, 100)
        
        # Calculate current vibe based on score
        if wellnessScore >= 80:
            currentVibe = "happy"
        elif wellnessScore >= 60:
            currentVibe = "tending to happy"
        elif wellnessScore >= 40:
            currentVibe = "neutral"
        elif wellnessScore >= 20:
            currentVibe = "sad"
        else:
            currentVibe = "angry"
            
        vector = [random.uniform(-1, 1) for _ in range(768)] # Assuming 768 dims
        
        user = User(
            empid=empid,
            email=f"{name.replace(' ', '.').lower()}@example.com",
            name=name,
            streakDays=random.randint(0, 30),
            wellnessScore=wellnessScore,
            numberOfteamMessages=random.randint(10, 500),
            numberOfemailsSent=random.randint(5, 300),
            dept=dept,
            role=role,
            joinedOn=fake.date_time_this_decade(),
            level=random.randint(1, 10),
            levelProgress=random.randint(0, 99),
            moodCalendar=[
                VibeEntry(moodLevel=random.randint(1, 5), timestamp=datetime.now() - timedelta(days=d))
                for d in range(5)
            ],
            recentTrends=TrendEntryArray(
                improvingTrend=TrendEntry(title="Improving Trend", description="Last 5 days", icon="trend-up"),
                consistentCheckIns=TrendEntry(title="Consistent Check-Ins", description=f"{random.randint(1, 10)} Day Streak", icon="check"),
                wellnessScore=TrendEntry(title="Wellness Score", description=f"{wellnessScore}/100", icon="heart")
            ),
            numberOfmeetingsAttended=random.randint(2, 50),
            workHours=random.randint(30, 60),
            currentVibe=currentVibe,
            vibeHistory=[],
            earnedBadges=[],
            badgesToUnlock=[],
            wellnessPoints=random.randint(100, 1000),
            changedThisWeek=random.randint(-10, 10),
            wellnessPointEntry=wellnessPointEntryArray(
                chatCheckIn=wellnessPointEntry(points=random.randint(10, 50), description="Chat Check-In"),
                wellnessActivities=wellnessPointEntry(points=random.randint(10, 50), description="Wellness Activities"),
                streakBonus=wellnessPointEntry(points=random.randint(10, 50), description="Streak Bonus")
            ),
            avaiableRewards=[],
            pastRewards=[],
            avatar=f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=random",
            leaves=[],
            awards=[],
            companyAwards=[],
            likedSounds=[],
            isStreakBonusUpdated=False,
            longTermMemory="",
            moodFactors=[],
            vectorEmbedding=vector
        )
        users_to_insert.append(user)

    print("Inserting users to database in chunks...")
    chunk_size = 100
    for i in range(0, len(users_to_insert), chunk_size):
        chunk = users_to_insert[i:i + chunk_size]
        await User.insert_many(chunk)
        print(f"Inserted {i + len(chunk)}/{num_users} users...")
        
    print("Users successfully populated!")
    
if __name__ == "__main__":
    asyncio.run(generate_users(1000))
