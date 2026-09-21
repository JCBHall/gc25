import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
from datetime import datetime
import os

from models.user import User
from models.admindb import Admindb, EmployeeMoodDistribution, DailyChatParticipation
from models.admindball import Admindball, BriefTotalUser
from models.admindbemp import Admindbemp, BriefUserDetails, PastMoodTrend, Badge, CompanyAward, LeaveHistory, ChatHistory
from models.auth import Auth
from models.adminAuth import Admin
from models.sound import Sounds
from models.meet import Meet
from models.queue import Queue

async def seed_admin():
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    if not hasattr(client.__class__, "append_metadata"):
        client.__class__.append_metadata = lambda *args, **kwargs: None
    db = client["gc25"]
    await init_beanie(database=db, document_models=[Auth, User, Admin, Admindb, Admindball, Admindbemp, Sounds, Meet, Queue])

    print("Fetching all users...")
    users = await User.find({}).to_list()
    
    print(f"Found {len(users)} users.")

    if len(users) == 0:
        print("No users found. Creating empty admin structures...")

    # Seed Admindb
    print("Seeding Admindb...")
    admindb = await Admindb.find_one({})
    if not admindb:
        admindb = Admindb(
            totalNumberOfEmp=len(users),
            noOfHappyEmp=0,
            noOfEscalatedIssues=0,
            totalChatInteractions=0,
            employeeMoodDistribution=EmployeeMoodDistribution(happy=0, tendingToHappy=0, neutral=0, sad=0, angry=0),
            dailyChatParticipation=[],
            hikeFromPrevMonth=0,
            briefEscalatedUsersList=[]
        )
        await admindb.insert()
        print("Created Admindb.")
    else:
        print("Admindb already exists. Updating total users...")
        admindb.totalNumberOfEmp = len(users)
        await admindb.save()

    # Seed Admindball
    print("Seeding Admindball...")
    admindball = await Admindball.find_one({})
    
    brief_users = []
    for u in users:
        brief_users.append(BriefTotalUser(
            name=u.name,
            empid=u.empid,
            dept=u.dept,
            lastActive=datetime.now(),
            currentMood="Neutral",
            isEscalated=False,
            briefMoodSummary="",
            avatarUrl=u.avatar
        ))

    if not admindball:
        admindball = Admindball(briefTotalUsersList=brief_users)
        await admindball.insert()
        print("Created Admindball.")
    else:
        print("Admindball already exists. Updating users list...")
        # Check and add missing users
        existing_empids = {u.empid for u in admindball.briefTotalUsersList}
        new_users = [u for u in brief_users if u.empid not in existing_empids]
        if new_users:
            admindball.briefTotalUsersList.extend(new_users)
            await admindball.save()
            print(f"Added {len(new_users)} new users to Admindball.")

    # Seed Admindbemp
    print("Seeding Admindbemp for each user...")
    for u in users:
        emp = await Admindbemp.find_one(Admindbemp.briefUserDetails.empid == u.empid)
        if not emp:
            emp = Admindbemp(
                briefUserDetails=BriefUserDetails(
                    name=u.name,
                    empid=u.empid,
                    dept=u.dept,
                    lastActive=datetime.now(),
                    currentMood="Neutral",
                    isEscalated=False,
                    briefMoodSummary="",
                    avatarUrl=u.avatar,
                    teamMessages=u.numberOfteamMessages,
                    emailsSent=u.numberOfemailsSent,
                    meetings=u.numberOfmeetingsAttended,
                    workHours=u.workHours
                ),
                pastFiveMoodTrends=[],
                currentMoodRate="",
                moodAnalysis="",
                recommendedAction="",
                earnedBadges=[],
                companyAwards=[],
                leaveHistory=[],
                chatHistory=[],
                chatAIAnalysis=""
            )
            await emp.insert()
            print(f"Created Admindbemp for {u.empid}")
        else:
            print(f"Admindbemp for {u.empid} already exists.")

    print("Admin database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_admin())
