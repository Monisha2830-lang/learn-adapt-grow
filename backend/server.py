from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import bcrypt
import jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class RegisterInput(BaseModel):
    name: str
    email: str
    password: str
    grade: str = "Grade 8"

class LoginInput(BaseModel):
    email: str
    password: str

class ProfileInput(BaseModel):
    name: str
    age: int
    grade: str

class QuizInput(BaseModel):
    subject: str
    topic: str
    grade: str
    history: List[str] = []

class AnswerInput(BaseModel):
    subject: str
    question: str
    answer: str
    correct_answer: str
    grade: str

SECRET = os.environ["JWT_SECRET"]

def token_for(user):
    return jwt.encode({"sub": user["email"], "exp": datetime.now(timezone.utc).timestamp() + 86400}, SECRET, algorithm="HS256")

SUBJECTS = [
    {"id":"math","name":"Mathematics","label":"Patterns & problem solving","icon":"∑","color":"indigo","progress":72,"next":"Linear equations","minutes":18},
    {"id":"science","name":"Science","label":"Explore how the world works","icon":"◉","color":"emerald","progress":48,"next":"Cells & systems","minutes":24},
    {"id":"english","name":"English","label":"Read, write, express","icon":"Aa","color":"amber","progress":64,"next":"Persuasive writing","minutes":15},
    {"id":"history","name":"History","label":"Connect the dots of time","icon":"⌁","color":"rose","progress":31,"next":"Industrial revolution","minutes":20},
    {"id":"computer-science","name":"Computer Science","label":"Think like a builder","icon":"<>_","color":"cyan","progress":12,"next":"Algorithms","minutes":27},
    {"id":"biology","name":"Biology","label":"Life in every detail","icon":"✣","color":"violet","progress":0,"next":"Start with the basics","minutes":22},
]

LESSONS = {
    "math": {"title":"Linear equations","subject":"Mathematics","eyebrow":"Next up · 18 min","summary":"A linear equation is a balanced statement where an unknown value can be found by making the same move to both sides.","steps":["Think of the equals sign as a perfectly balanced scale.","Undo operations in reverse order: subtract before dividing.","Always check by putting your answer back into the original equation."],"example":"3x + 4 = 19  →  3x = 15  →  x = 5"},
    "science": {"title":"Cells & systems","subject":"Science","eyebrow":"Continue · 24 min","summary":"Cells are the smallest living units. Their specialized parts work together like a tiny, organized city.","steps":["The cell membrane decides what enters and leaves.","The nucleus stores instructions for the cell.","Mitochondria release energy from food for the cell to use."],"example":"Cell membrane → controls traffic | Nucleus → stores instructions"},
}

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "SynapseLearn API is ready"}

@api_router.post("/auth/register")
async def register(input: RegisterInput):
    existing = await db.users.find_one({"email": input.email.lower()}, {"_id": 0})
    if existing: raise HTTPException(400, "An account with this email already exists")
    user = {"id": str(uuid.uuid4()), "name": input.name, "email": input.email.lower(), "password": bcrypt.hashpw(input.password.encode(), bcrypt.gensalt()).decode(), "grade": input.grade, "age": 13, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(user.copy())
    return {"token": token_for(user), "user": {k:user[k] for k in ["id","name","email","grade","age"]}}

@api_router.post("/auth/login")
async def login(input: LoginInput):
    user = await db.users.find_one({"email": input.email.lower()}, {"_id": 0})
    if not user or not bcrypt.checkpw(input.password.encode(), user["password"].encode()): raise HTTPException(401, "Email or password is incorrect")
    return {"token": token_for(user), "user": {k:user[k] for k in ["id","name","email","grade","age"]}}

@api_router.post("/auth/google")
async def google_login():
    user = {"id":"google-demo", "name":"Alex Morgan", "email":"alex@demo.synapselearn.com", "grade":"Grade 8", "age":13}
    return {"token": token_for(user), "user": user}

@api_router.get("/subjects")
async def subjects(): return SUBJECTS

@api_router.get("/lessons/{subject_id}")
async def lesson(subject_id: str): return LESSONS.get(subject_id, {"title":"Foundations","subject":"Study session","eyebrow":"Personalized · 20 min","summary":"Build a strong foundation with a short, focused lesson made for your current level.","steps":["Start with one clear idea.","Connect it to something you already know.","Practice once, then explain it in your own words."],"example":"Learn → connect → practice → remember"})

@api_router.post("/quiz")
async def quiz(input: QuizInput):
    if input.subject.lower() == "mathematics":
        return {"question":"If 3x + 4 = 19, what is x?","options":["3","5","7","15"],"correct":"5","topic":input.topic or "Linear equations","difficulty":"Just right","hint":"Undo the +4 first, then divide by 3."}
    return {"question":"Which choice best describes the key idea from this lesson?","options":["It works only in special cases","It is a system of connected parts","It is impossible to test","It is unrelated to evidence"],"correct":"It is a system of connected parts","topic":input.topic or "Core concepts","difficulty":"Just right","hint":"Think about how the parts work together."}

@api_router.post("/explain")
async def explain(input: AnswerInput):
    correct = input.answer == input.correct_answer
    fallback = ("Exactly — you found the right relationship. Try saying it once in your own words so it sticks." if correct else f"Not quite. Start by identifying the operation or idea that changes first. The answer is {input.correct_answer}. Revisit the example, then try a similar one.")
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key: return {"correct":correct,"explanation":fallback,"source":"personalized tutor"}
    try:
        chat = LlmChat(api_key=key, session_id=f"explain-{uuid.uuid4()}", system_message="You are a warm school tutor. Give a concise, age-appropriate explanation in 2 sentences. Celebrate effort, explain the reasoning, and never shame the learner.").with_model("openai", "gpt-5.6-luna")
        text = ""
        async for event in chat.stream_message(UserMessage(text=f"Grade: {input.grade}. Subject: {input.subject}. Question: {input.question}. Student answer: {input.answer}. Correct answer: {input.correct_answer}.")):
            if isinstance(event, TextDelta): text += event.content
        if text: fallback = text
    except Exception: pass
    return {"correct":correct,"explanation":fallback,"source":"personalized tutor"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()