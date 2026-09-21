import json
import pymongo
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "gc25"

def parse_date(date_str):
    if not date_str:
        return datetime.utcnow()
    try:
        # if it's already ISO format or similar
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    return datetime.utcnow()

def seed():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    user_col = db["user"]

    print("Loading employees.json...")
    with open("data/employees.json", "r") as f:
        employees = json.load(f)

    print("Loading moods.json...")
    with open("data/moods.json", "r") as f:
        moods = json.load(f)

    for emp in employees:
        empid = emp.get("empid")
        if not empid:
            continue
            
        # Add email placeholder if missing
        if "email" not in emp:
            emp["email"] = f"{empid.lower()}@example.com"
            
        # Parse joinedOn date
        if "joinedOn" in emp and isinstance(emp["joinedOn"], str):
            emp["joinedOn"] = parse_date(emp["joinedOn"])
            
        # Update mood data
        mood_data = moods.get(empid)
        if mood_data:
            emp["wellnessScore"] = mood_data.get("moodScore", emp.get("wellnessScore", 50))
            emp["moodFactors"] = mood_data.get("moodFactors", [])
            
        # Ensure datetimes inside lists (like moodCalendar) are parsed correctly
        if "moodCalendar" in emp:
            for v in emp["moodCalendar"]:
                if "timestamp" in v and isinstance(v["timestamp"], str):
                    v["timestamp"] = parse_date(v["timestamp"])
                    
        # Replace or insert
        user_col.replace_one({"empid": empid}, emp, upsert=True)
        
    print(f"Seeded {len(employees)} employees into the 'user' collection.")

if __name__ == "__main__":
    seed()

