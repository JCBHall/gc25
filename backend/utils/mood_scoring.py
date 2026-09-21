import asyncio
import json
import re
import google.generativeai as genai
from config import settings
import logging

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

QUESTION_BANK = {
    "I. Workload & Role Clarity": [
        "How would you describe your current workload? Is it manageable, overwhelming, or unpredictable?",
        "Have your responsibilities shifted recently in ways that feel unclear or unsustainable?",
        "What percentage of your workweek is spent on tasks that align with your core strengths?",
        "Do you have the tools/resources needed to meet client or project expectations effectively?",
        "How often do you work beyond standard hours to meet deadlines?",
        "Are you involved in overlapping projects that create conflicting priorities?"
    ],
    "II. Recognition & Career Growth": [
        "When was the last time you received meaningful recognition for your contributions?",
        "Do you feel your career progression aligns with your current role and aspirations?",
        "What opportunities (training, certifications, mentorship) would help you grow here?",
        "How transparent is the promotion process in your practice area?",
        "Have you discussed your career goals with your manager in the past six months?",
        "Do you feel your skills are underutilized in your current projects?"
    ],
    "III. Well-being & Work-Life Balance": [
        "How often does work stress impact your personal life or health?",
        "Are you able to fully disconnect during vacations or weekends?",
        "Have you taken unplanned leave recently due to work-related fatigue?",
        "How supportive is Deloitte in accommodating personal/family needs?",
        "What changes to your schedule or workload would improve your well-being?",
        "Do you feel pressured to prioritize client demands over personal health?"
    ],
    "IV. Relationships & Team Dynamics": [
        "How would you rate your communication with your direct manager?",
        "Do you feel comfortable voicing concerns or ideas in team settings?",
        "Have recent team changes (e.g., new leadership, restructuring) affected your morale?",
        "How inclusive is your team's culture in valuing diverse perspectives?",
        "Are there unresolved conflicts affecting collaboration on your projects?",
        "Do you feel socially connected to your peers, or isolated in your role?"
    ],
    "V. Alignment & Feedback": [
        "What feedback have you received that you feel was unfair or unclear?",
        "How actionable is the feedback you receive from managers or peers?",
        "Would you recommend Deloitte as a workplace to others in your network? Why or why not?",
        "What one policy change would most improve your day-to-day experience?",
        "If you could redesign your role, what would you prioritize?",
        "How closely do your daily tasks align with Deloitte's stated values (e.g., sustainability, integrity)?"
    ]
}

formatted_questions = []
for category, questions in QUESTION_BANK.items():
    formatted_questions.append(f"{category}")
    for i, question in enumerate(questions, 1):
        formatted_questions.append(f"{i}. {question}")
    formatted_questions.append("")
questions_text = "\n".join(formatted_questions)

async def get_recommended_question(user):
    prompt = f\"\"\"
    Analyze the following employee mood data and select exactly ONE question from the question bank 
    that would be most appropriate to ask this employee based on their mood factors and score.
    
    Employee ID: {user.empid}
    Mood Score: {user.wellnessScore}/100
    Mood Factors:
    {json.dumps(user.moodFactors, indent=2)}
    
    Question Bank:
    {questions_text}
    
    IMPORTANT: Your task is to select EXACTLY ONE question from the question bank above that is most relevant 
    to this employee's situation. DO NOT modify or create new questions. The selected question must be word-for-word 
    from the question bank. Now PERSONALIZE that question with user's moodScore and moodFactors
    
    Format your response ONLY as:
    QUESTION: [copy and paste the exact personalized question]
    \"\"\"
    
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        question_match = re.search(r"QUESTION:\s*(.+?)(?=CATEGORY:|$)", response.text, re.DOTALL)
        if question_match:
            return question_match.group(1).strip()
    except Exception as e:
        logger.error(f"Error calling Gemini for {user.empid}: {e}")
    
    return "How are you feeling today?"

async def process_analytics_and_queue(user_model, queue_model, queue_user_model):
    logger.info("Starting employee analytics for queueing...")
    
    queue = await queue_model.find_one({})
    if not queue:
        queue = queue_model()
        await queue.insert()
        
    users = await user_model.find_all().to_list()
    queued_count = 0
    
    for user in users:
        if user.wellnessScore <= 45:
            logger.info(f"Analyzing {user.empid} (Score: {user.wellnessScore})...")
            question = await get_recommended_question(user)
            
            new_q_user = queue_user_model(
                empid=user.empid,
                emailID=user.email or f"{user.empid.lower()}@example.com",
                message=question,
                empName=user.name
            )
            queue.users.append(new_q_user)
            queued_count += 1
            
            # Rate limiting delay for Gemini
            await asyncio.sleep(2)
            
    await queue.save()
    logger.info(f"Analytics complete. Added {queued_count} users to the mail queue.")
