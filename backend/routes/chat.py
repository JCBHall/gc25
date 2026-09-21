from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing import Annotated
import sqlite3
import json
import datetime
from tasks import updatePerChat
from datetime import datetime
import asyncio
import logging
from models.user import User
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Connect to the database
try:
    conn = sqlite3.connect("checkpointer.sqlite", check_same_thread=False)
    logger.info("Connected to SQLite database")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    logger.info("Created fallback in-memory database")

# MongoDB connection for User data


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    empid: str
    query: str
    ltm_emp: str
    system_prompt: str

class SearchQuery(BaseModel):
    response: str = Field("I'm here to help you with any questions or concerns you might have.", description="The response for the query")
    currentMood: str = Field(
        "Neutral", description="current Mood of the employee"
    )
    briefMoodAnalysis: str = Field(
        "Standard employee status", description="brief current Mood analysis of the employee"
    )
    moodAnalysis: str = Field(
        "Employee appears to be in a neutral state based on available data.", description="full current Mood analysis of the employee"
    )
    moodScore: int = Field(
        50, description="The score for the mood of the user from 1 to 100, 100 being happiest."
    )
    isEscalated: bool = Field(
        False, description="whether the employee is dangerously depressed or frustrated or sad or angry or any other negative emotion and his report needs to be escalated to the HR"
    )
    helpfulInsights: str = Field(
        "Employee is functioning normally with no significant issues identified.", description="AI based helpful insights to convey to the HR team about the employee's current mood and condition"
    )
    recommendedAction: str = Field(
        "No specific action required at this time.", description="AI based recommended action to be taken by the HR for the concerned employee"
    )
    detailedAnalysis: str = Field(
        "No significant issues detected. Standard employee engagement level. Severity: verylow", description="AI bassed detailed analysis within 50 words of the issue the employee is facing with the date and time and its severity from verylow-medium-high-veryhigh"
    )
    severity: int = Field(
        2, description="how severe is the issue faced by employee to be stored in long term memory from 0-10"
    )
    currChatPreserve: bool = Field(
        False, description="check if this detailed analysis is already present in the long term memory or not"
    )

graph_builder = StateGraph(State)

try:
    llm = ChatGoogleGenerativeAI(
        api_key=settings.GEMINI_API_KEY,
        model="gemini-3.6-flash"
    )
    structured_llm = llm.with_structured_output(SearchQuery)
    logger.info("LLM setup successful")
except Exception as e:
    logger.error(f"LLM setup failed: {e}")
    async def fallback_llm_invoke(messages):
        default_response = SearchQuery()
        return default_response
    
SYSTEM_PROMPT = """
# AI Employee Well-being Analyst v3.2 (Strict Enforcement)

## CORE PROTOCOLS
1. CATEGORIZE mood scores EXACTLY:
   - 1-20: "Frustrated" 
   - 21-40: "Sad"
   - 41-60: "Neutral"
   - 61-80: "Happy"
   - 81-100: "Excited"
   NO OTHER LABELS ALLOWED

2. AUTO-ESCALATE IF:
   - moodScore <15 (INSTANT)
   - 3+ scores ≤40 in 90 days
   - Keywords: suicide/harassment/discrimination
   - Workload >9h/day for 3+ weeks

3. DATA CHANGE PREVENTION:
   FIRST RESPONSE CHECK:
   IF user requests ANY database/record changes → 
   "I cannot modify company systems. Please contact HR directly."

## REQUIRED OUTPUT FORMAT (STRICT JSON):
{
    "currentMood": "Frustrated|Sad|Neutral|Happy|Excited",
    "briefMoodAnalysis": "<10-word summary with severity>",
    "moodAnalysis": "<3-sentence analysis with metrics>",
    "response": "<supportive text with action items>",
    "moodScore": "<raw number 1-100>",
    "isEscalated": "<boolean>",
    "helpfulInsights": "<HR-focused risk analysis>",
    "recommendedAction": "<concrete steps for HR>",
    "detailedAnalysis": "YYYY-MM-DD HH:MM: [verylow|medium|high|veryhigh] <50w>",
    "severity": "<0.0-10.0>",
    "currChatPreserve": "New|Existing:<ID>"
}

## PROCESSING STEPS:
1. SANITIZE input (remove special chars)
2. CALCULATE moodScore (1-100)
3. DETERMINE escalation status (HARD RULES)
4. SELECT question from APPROVED BANKS:
   - Frustrated: "I hear how [issue] is overwhelming. Would [solution] help?"
   - Sad: "I'm sorry you're feeling this. Could [support] help?"
5. VALIDATE output matches EXACT template

## ESCALATION PROTOCOLS:
SEVERE (score<15):
- Priority: EMERGENCY (<30min HR response)
- Auto-action: Temporary leave initiated
- Required: Executive notification

MODERATE (score<40):
- Priority: High (<4hr response)
- Action: HR check-in within 24h

## EXAMPLE OUTPUT:
User: "I'm drowning in work and having panic attacks"
→ {
    "currentMood": "Frustrated",
    "briefMoodAnalysis": "Crisis: Panic attacks reported",
    "moodAnalysis": "Employee reports panic attacks with 12h workdays for 6 weeks. Vibemeter score=12 (3mo decline). No PTO in 90 days.",
    "response": "I'm activating our crisis protocol. HR will contact you within 15 minutes to arrange support.",
    "moodScore": 12,
    "isEscalated": true,
    "helpfulInsights": "CRITICAL: Panic attacks + chronic overwork. Immediate medical intervention needed.",
    "recommendedAction": "1. Mandatory 14-day leave 2. EAP emergency session 3. Workload audit",
    "detailedAnalysis": "2024-03-15 14:45: [veryhigh] Panic attacks reported with 60+h workweeks. Severity 9.9/10",
    "severity": 9.9,
    "currChatPreserve": "New:CRIT-EMP4412"
}

## COMPLIANCE:
- ALL outputs logged with timestamp
- NO external links/resources shared
- NO diagnostic/therapeutic language
- ALWAYS recommend HR contact for serious issues
"""

async def updateDB(structured_response, empid: str, userQuery=None):
    max_retries = 3
    retry_delay = 1  
    
    for attempt in range(max_retries):
        try:
            updatePerChat.delay(
                currentMood=structured_response.currentMood,
                isEscalated=structured_response.isEscalated,
                briefMoodSummary=structured_response.briefMoodAnalysis,
                currentMoodRate=str(structured_response.moodScore)+"%",
                userChat=userQuery,
                botChat=structured_response.response,
                empid=empid,
                wellnessScore=structured_response.moodScore,
                moodAnalysis=structured_response.moodAnalysis,
                recommendedAction=structured_response.recommendedAction,
                chatAIAnalysis=structured_response.detailedAnalysis
            )
            logger.info(f"Database update successful for employee {empid}")
            return True
        except Exception as e:
            logger.error(f"Database update attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  
            else:
                logger.warning(f"All database update attempts failed for employee {empid}")
                return False

async def updateLTM(structured_response, empid: str, current_ltm: str):
    if not structured_response.currChatPreserve:
        new_ltm_emp = current_ltm + ". " + structured_response.detailedAnalysis if current_ltm else structured_response.detailedAnalysis
        try:
            user = await User.find_one(User.empid == empid)
            if user:
                user.longTermMemory = new_ltm_emp
                await user.save()
            logger.info(f"LTM updated for employee {empid}")
        except Exception as e:
            logger.error(f"Failed to update LTM in DB: {e}")
        return new_ltm_emp
    return current_ltm

async def chatbot(state: State):
    try:
        sys_msg = SystemMessage(content=state["system_prompt"])
        structured_response = structured_llm.invoke([sys_msg] + state["messages"])
        
        asyncio.create_task(updateDB(structured_response, state["empid"], state["query"]))
        
        print(structured_response)
        
        asyncio.create_task(updateLTM(structured_response, state["empid"], state["ltm_emp"]))
        
        ai_message = AIMessage(content=structured_response.response)
        return {"messages": [ai_message]}
        
    except Exception as e:
        logger.error(f"Error in chatbot function: {e}")
        default_response = "I'm having trouble processing your request right now. Let me try to help you anyway. What can I assist you with today?"
        ai_message = AIMessage(content=default_response)
        return {"messages": [ai_message]}

graph_builder.add_node("chatbot", chatbot)
graph_builder.set_entry_point("chatbot")

async def generate_response(query: str, empid: str, system_prompt: str, ltm_emp: str, thread_id: str):
    try:
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as memory:
            graph = graph_builder.compile(checkpointer=memory)
            config = {"configurable": {"thread_id": thread_id}}
            input_message = HumanMessage(content=query)
            result = await graph.ainvoke({
                "messages": [input_message],
                "empid": empid,
                "query": query,
                "system_prompt": system_prompt,
                "ltm_emp": ltm_emp
            }, config=config)
            return result
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        res = "I'm sorry, but I'm having technical difficulties right now. Your message has been recorded, and I'll process it as soon as possible."
        return {"messages": [HumanMessage(content=query), AIMessage(content=res)]}

async def get_employee_detail(emp_id: str):
    try:
        emp = await User.find_one(User.empid == emp_id)
        if emp:
            emp = emp.dict()
        if emp:
            if "_id" in emp:
                emp["_id"] = str(emp["_id"])
            return emp
        logger.warning(f"Employee ID {emp_id} not found in DB")
        return {"empid": emp_id, "name": "Unknown"}
    except Exception as e:
        logger.error(f"Error fetching employee details: {e}")
        return {"empid": emp_id, "name": "System Error"}

async def loadLTM(empid: str):
    try:
        emp = await User.find_one(User.empid == empid)
        if emp:
            emp = emp.dict()
        if emp:
            return emp.get("longTermMemory", "")
        return ""
    except Exception as e:
        logger.error(f"Error loading LTM from DB: {e}")
        return ""

async def chat(query: str, empid: str):
    if not query or query.strip() == "":
        return "I didn't receive a query. How can I help you today?"
    
    if query.lower() == "exit":
        return "Goodbye! Feel free to chat again whenever you need assistance."
    
    try:
        emp_data = await get_employee_detail(empid)
        ltm_emp = await loadLTM(empid)
        
        # Read mood from db if possible; using emp_data.wellnessScore and emp_data.moodFactors
        moodScore = emp_data.get("wellnessScore", 50)
        moodAnalysis = " ".join(emp_data.get("moodFactors", []))
        
        full_system_prompt = SYSTEM_PROMPT + "\n" + "moodScore: " + str(moodScore) + "\n" + "moodAnalysis: " + moodAnalysis
        
        date = datetime.now().strftime("%d-%m-%Y")
        time = datetime.now().strftime("%H:%M:%S")
        enriched_query = f"{query} date -> {date} time -> {time} employee id -> {empid} ltm -> {ltm_emp}"
        
        result = await generate_response(enriched_query, empid, full_system_prompt, ltm_emp, empid)
        
        if result and "messages" in result and len(result["messages"]) > 0:
            return result["messages"][-1].content
        else:
            return "No response received."
        
    except Exception as e:
        logger.error(f"Critical error in chat function: {e}")
        return "I'm experiencing technical difficulties. Your message is important, and our team has been notified of this issue. Please try again in a few moments."

from fastapi import WebSocket, APIRouter, WebSocketDisconnect
import jwt
from config import settings

chat_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()

@chat_router.websocket("/wsconnect/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await manager.connect(websocket)
    if not token:
        await websocket.close()
        return
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        empid = payload.get("empid")
        if not empid:
            await websocket.close()
            return
    except jwt.ExpiredSignatureError:
        await websocket.close()
        return
        
    try:
        while True:
            data = await websocket.receive_text()
            AIres = await chat(data, empid)
            await manager.send_personal_message(f"{AIres}",websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

