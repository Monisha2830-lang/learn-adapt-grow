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

class HistoryInput(BaseModel):
    email: str
    kind: str
    subject: str
    topic: str
    correct: Optional[bool] = None
    answer: Optional[str] = None

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
    "math": {"title":"Linear equations","subject":"Mathematics","eyebrow":"Next up · 18 min","summary":"A linear equation is a balanced statement where an unknown value can be found by making the same move to both sides.","steps":["Think of the equals sign as a perfectly balanced scale.","Find the unknown letter before you start calculating.","Undo addition by subtracting the same number.","Undo subtraction by adding the same number.","Undo multiplication by dividing both sides.","Undo division by multiplying both sides.","Always do the same operation to both sides.","Write each small step on its own line.","Check by putting your answer into the original equation."],"example":"3x + 4 = 19  →  3x = 15  →  x = 5"},
    "science": {"title":"Cells & systems","subject":"Science","eyebrow":"Continue · 24 min","summary":"Cells are the smallest living units. Their specialized parts work together like a tiny, organized city.","steps":["The cell membrane decides what enters and leaves.","The cytoplasm is where many cell jobs happen.","The nucleus stores instructions for the cell.","Mitochondria release usable energy from food.","Ribosomes help build proteins the cell needs.","Plant cells have chloroplasts for capturing light energy.","A cell wall gives plant cells extra support.","Cells work together in tissues and organs.","Structure and function explain why each part matters."],"example":"Cell membrane → controls traffic | Nucleus → stores instructions"},
    "english": {"title":"Persuasive writing","subject":"English","eyebrow":"Next up · 15 min","summary":"Persuasive writing uses a clear opinion, strong reasons, and evidence to help a reader understand your point of view.","steps":["State your opinion clearly in the opening.","Know who your reader is.","Give one main reason at a time.","Support reasons with specific evidence.","Use linking words to guide the reader.","Acknowledge another view respectfully.","Choose precise, confident words.","Read your draft aloud for clarity.","Finish by showing why the idea matters."],"example":"Claim + reasons + evidence = convincing writing"},
    "history": {"title":"Industrial revolution","subject":"History","eyebrow":"Continue · 20 min","summary":"The Industrial Revolution changed how people made goods, worked, and lived by moving production into factories.","steps":["Machines made production faster.","Factories brought workers together in cities.","Coal and steam powered early growth.","Textiles were among the first industries transformed.","Railways connected suppliers, workers, and customers.","Cities grew quickly around new jobs.","Working conditions were often difficult.","Reform movements pushed for safer workplaces.","The changes created both opportunity and inequality."],"example":"New machines → factories → growing cities"},
    "computer-science": {"title":"Algorithms","subject":"Computer Science","eyebrow":"Start here · 27 min","summary":"An algorithm is a clear set of steps that solves a problem, like a recipe that a computer can follow.","steps":["Name the problem before choosing steps.","Identify the information you start with.","Break the task into small actions.","Keep each step clear and in order.","Use choices when different cases need different actions.","Repeat steps when a task happens more than once.","Test the process with a small example.","Notice where the process could be faster.","Explain the output so another person can check it."],"example":"Input → steps → output"},
    "biology": {"title":"Life foundations","subject":"Biology","eyebrow":"Start here · 22 min","summary":"Living things are organized systems that use energy, respond to their surroundings, and grow or reproduce.","steps":["Cells are the basic units of life.","Living systems need energy to keep working.","Cells use instructions to make useful proteins.","Organisms respond to changes around them.","Stable internal conditions help life continue.","Groups of cells can form tissues.","Tissues work together in organs.","Organisms grow and reproduce in different ways.","Structure and function are connected."],"example":"Structure helps a living thing do its job"},
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
        questions = [{"question":"If 3x + 4 = 19, what is x?","options":["3","5","7","15"],"correct":"5","explanation":"Subtract 4 to get 15, then divide by 3. So x = 5."},{"question":"What is 2/4 in its simplest form?","options":["1/2","1/4","2/8","4/2"],"correct":"1/2","explanation":"Divide the top and bottom by 2: 2/4 becomes 1/2."},{"question":"What is the next number: 2, 4, 8, 16, __?","options":["18","24","32","34"],"correct":"32","explanation":"Each number doubles, so 16 × 2 = 32."},{"question":"Which is equal to 0.75?","options":["1/4","3/4","7/5","75/10"],"correct":"3/4","explanation":"0.75 means 75 hundredths, which simplifies to 3/4."},{"question":"A triangle has angles 60° and 70°. What is the third angle?","options":["40°","50°","60°","70°"],"correct":"50°","explanation":"Triangle angles total 180°. 180 − 60 − 70 = 50°."}]
    else:
        questions = [{"question":"Which choice best describes the key idea from this lesson?","options":["It works only in special cases","It is a system of connected parts","It is impossible to test","It is unrelated to evidence"],"correct":"It is a system of connected parts","explanation":"The lesson connects smaller ideas into one working system."},{"question":"Which study move helps memory most?","options":["Read once and stop","Explain it in your own words","Skip examples","Guess quickly"],"correct":"Explain it in your own words","explanation":"Explaining aloud helps your brain organize and retrieve the idea."},{"question":"What should you do when an answer is difficult?","options":["Give up","Look for a clue and try a smaller step","Delete the question","Choose randomly"],"correct":"Look for a clue and try a smaller step","explanation":"Small steps reduce the load and reveal what you already know."},{"question":"Why do we use examples?","options":["To decorate notes","To connect an idea to a real case","To make lessons longer","To avoid thinking"],"correct":"To connect an idea to a real case","explanation":"Examples turn an abstract idea into something easier to picture."},{"question":"What makes a strong study note?","options":["One giant paragraph","A clear idea and a short example","Only difficult words","No headings"],"correct":"A clear idea and a short example","explanation":"A simple idea plus an example is easier to revisit later."}]
    return {"questions":questions,"question":questions[0]["question"],"options":questions[0]["options"],"correct":questions[0]["correct"],"topic":input.topic or "Core concepts","difficulty":"Just right","hint":"Use the lesson’s core idea, then eliminate choices that do not fit."}

@api_router.post("/history")
async def save_history(input: HistoryInput):
    doc = input.model_dump(); doc["created_at"] = datetime.now(timezone.utc).isoformat(); await db.study_history.insert_one(doc)
    return {"saved": True, "id": str(uuid.uuid4())}

@api_router.get("/review-queue/{email}")
async def review_queue(email: str):
    attempts = await db.study_history.find({"email": email, "kind": "quiz", "correct": False}, {"_id": 0}).to_list(20)
    topics = list({a.get("topic", "Core concepts") for a in attempts})
    return {"items":[{"topic":t,"reason":"A gentle revisit can make this one stick","subject":next((s["name"] for s in SUBJECTS if s["name"].lower() in t.lower()),"Your subject")} for t in topics[:5]] or [{"topic":"Linear equations","reason":"A short revisit builds confidence","subject":"Mathematics"},{"topic":"Cells & systems","reason":"Review while it is still fresh","subject":"Science"}]}

@api_router.get("/progress-insights/{email}")
async def progress_insights(email: str):
    attempts = await db.study_history.find({"email": email, "kind": "quiz"}, {"_id": 0}).to_list(100)
    by_topic = {}
    for item in attempts:
        topic = item.get("topic", "Core concepts"); stats = by_topic.setdefault(topic, {"correct":0,"total":0}); stats["total"] += 1; stats["correct"] += int(bool(item.get("correct")))
    return {"insights":[{"topic":t,"score":round(v["correct"] / v["total"] * 100),"message":"Strong foundation — try a harder example next." if v["correct"] else "Try one more small example, then explain it aloud."} for t,v in by_topic.items()]}

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