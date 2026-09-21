from fastapi import APIRouter
from models.auth import Auth, AuthAuth
import bcrypt
import datetime
import jwt
import logging
from config import settings
from fastapi.responses import JSONResponse

auth_router = APIRouter()

logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)

def create_response(success: bool, message: str, data=None, code=200):
    return JSONResponse(content={"success": success, "message": message, "data": data, "code": code}, status_code=code)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

async def encode_empid(empid: str) -> str:
    payload = {
        "empid": empid,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

from models.user import User, TrendEntry, TrendEntryArray, wellnessPointEntry, wellnessPointEntryArray
from models.admindbemp import Admindbemp, BriefUserDetails

@auth_router.post("/signup")
async def signup_user(auth: AuthAuth):
    try:
        existing_user = await Auth.find_one(Auth.empid == auth.empid)
        if existing_user:
            logger.warning(f"Signup attempt failed: User {auth.empid} already exists")
            return create_response(False, "User already exists", code=400)

        hashpwd = hash_password(auth.password)
        new_user = Auth(empid=auth.empid, password=hashpwd, token="")
        await new_user.insert()

        # Provision a default User profile
        user_profile = User(
            empid=auth.empid,
            email=f"{auth.empid}@example.com",
            name=auth.empid,
            streakDays=0,
            wellnessScore=50,
            numberOfteamMessages=0,
            numberOfemailsSent=0,
            dept="New Employee",
            role="Employee",
            joinedOn=datetime.datetime.now(),
            level=1,
            levelProgress=0,
            moodCalendar=[],
            recentTrends=TrendEntryArray(
                improvingTrend=TrendEntry(title="Improving Trend", description="No data", icon="trend-up"),
                consistentCheckIns=TrendEntry(title="Consistent Check-Ins", description="0 Day Streak", icon="check"),
                wellnessScore=TrendEntry(title="Wellness Score", description="50/100", icon="heart")
            ),
            numberOfmeetingsAttended=0,
            workHours=0,
            currentVibe="neutral",
            vibeHistory=[],
            earnedBadges=[],
            badgesToUnlock=[],
            wellnessPoints=0,
            changedThisWeek=0,
            wellnessPointEntry=wellnessPointEntryArray(
                chatCheckIn=wellnessPointEntry(points=0, description="Chat Check-In"),
                wellnessActivities=wellnessPointEntry(points=0, description="Wellness Activities"),
                streakBonus=wellnessPointEntry(points=0, description="Streak Bonus")
            ),
            avaiableRewards=[],
            pastRewards=[],
            avatar=f"https://ui-avatars.com/api/?name={auth.empid}&background=random",
            leaves=[],
            awards=[],
            companyAwards=[],
            likedSounds=[],
            isStreakBonusUpdated=False,
            longTermMemory="",
            moodFactors=[],
            vectorEmbedding=[0.0]*768
        )
        await user_profile.insert()

        # Provision a default Admindbemp profile
        emp_profile = Admindbemp(
            briefUserDetails=BriefUserDetails(
                name=auth.empid,
                empid=auth.empid,
                dept="New Employee",
                lastActive=datetime.datetime.now(),
                currentMood="neutral",
                isEscalated=False,
                briefMoodSummary="New employee",
                avatarUrl=f"https://ui-avatars.com/api/?name={auth.empid}&background=random",
                teamMessages=0,
                emailsSent=0,
                meetings=0,
                workHours=0
            ),
            pastFiveMoodTrends=[],
            currentMoodRate="neutral",
            moodAnalysis="No data available",
            recommendedAction="None",
            earnedBadges=[],
            companyAwards=[],
            leaveHistory=[],
            chatHistory=[],
            chatAIAnalysis=""
        )
        await emp_profile.insert()

        logger.info(f"User {auth.empid} created and provisioned successfully")
        return create_response(True, "User created successfully", code=201)

    except Exception as e:
        logger.error(f"Signup error: {str(e)}", exc_info=True)
        return create_response(False, "Internal server error", code=500)

@auth_router.post("/signin")
async def signin_user(auth: AuthAuth):
    try:
        user = await Auth.find_one(Auth.empid == auth.empid)
        if not user:
            logger.warning(f"Signin failed: User {auth.empid} does not exist")
            return create_response(False, "User does not exist", code=401)

        if not verify_password(auth.password, user.password):
            logger.warning(f"Signin failed: Invalid password for {auth.empid}")
            return create_response(False, "Invalid password", code=403)

        token = await encode_empid(auth.empid)
        user.token = token
        await user.save()

        logger.info(f"User {auth.empid} signed in successfully")
        
        return create_response(True, "Login successful", data={"token": token})

    except Exception as e:
        logger.error(f"Signin error: {str(e)}", exc_info=True)
        return create_response(False, "Internal server error", code=500)
