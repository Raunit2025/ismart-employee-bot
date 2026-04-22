from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
# from langdetect import detect
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from sqlalchemy.orm import Session

# Import our new database modules
from database import engine, get_db, SessionLocal
import models

# Create the database tables
models.Base.metadata.create_all(bind=engine)

# TEMPORARY: Create a test user on startup
db = SessionLocal()
if not db.query(models.User).filter(models.User.employee_id == "EMP101").first():
    db.add(models.User(employee_id="EMP101", name="Ashi Saxena", language_preference="en"))
    db.commit()
db.close()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

print("Loading translation model... This might take a minute on first boot.")
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
translator_model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")

LANG_MAP = {
    "hi": "hin_Deva", "mr": "mar_Deva", "bn": "ben_Beng", "en": "eng_Latn"
}

class ChatRequest(BaseModel):
    message: str
    employee_id: str
    language: str

SYSTEM_PROMPT = """You are the iSmart Facitech Employee Support Chatbot. 
Categorize the user's issue strictly into one of these exact departments based on the SOP:
- Salary & Payroll (High priority): Missing salary, overtime, payslips, PF, ESIC.
- Attendance & Leave (Medium priority): Mismatches, leave balances, shifts.
- HR & Employment (Medium priority): ID cards, uniforms, shoes, appointment letters, transfers.
- Workplace Issues (Critical priority): Harassment, supervisor asking for money, bribery, safety.
- General Queries (Low priority): Holiday lists, policy questions.

CRITICAL INSTRUCTION: You must ONLY output exactly 'Critical', 'High', 'Medium', or 'Low' for the priority.
Respond STRICTLY in this exact format:
Category: [Department]
Priority: [Priority Level]
Response: [Your brief, professional response to the employee]
"""

def translate_text(text, src_lang, tgt_lang):
    if src_lang == tgt_lang: return text
    tokenizer.src_lang = src_lang
    inputs = tokenizer(text, return_tensors="pt")
    tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)
    translated_tokens = translator_model.generate(**inputs, forced_bos_token_id=tgt_lang_id, max_length=200)
    return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]

@app.post("/chat")
def chat_with_bot(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. User Auth Check
    user = db.query(models.User).filter(models.User.employee_id == request.employee_id).first()
    if not user:
        return {"reply": "Error: Employee ID not found. Please log in with a valid ID."}

    original_text = request.message
    nllb_src_lang = request.language # We trust the frontend now!

    # 2. Translate to English for the AI
    english_input = translate_text(original_text, nllb_src_lang, "eng_Latn") if nllb_src_lang != "eng_Latn" else original_text

    # 3. AI Processing
    payload = {
        "model": "phi3",
        "prompt": f"{SYSTEM_PROMPT}\n\nEmployee: {english_input}\nChatbot:",
        "stream": False,
        "options": {"stop": ["Employee:", "\n\nEmployee:", "User:"]}
    }
    
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        bot_english_reply = response.json().get("response", "Error generating response.")
        
        # 4. Parse Output
        lines = bot_english_reply.strip().split('\n')
        category_val = "General Queries"
        priority_val = "Low"
        response_text = bot_english_reply 
        
        for line in lines:
            if line.startswith("Category:"): category_val = line.replace("Category:", "").strip()
            elif line.startswith("Priority:"): priority_val = line.replace("Priority:", "").strip()
            elif line.startswith("Response:"): response_text = line.replace("Response:", "").strip()

        # 5. Save Ticket to Database
        new_ticket = models.Ticket(
            user_id=user.id,
            category=category_val,
            priority=priority_val
        )
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)

        db.add(models.Message(ticket_id=new_ticket.id, sender="employee", content=original_text))
        db.add(models.Message(ticket_id=new_ticket.id, sender="bot", content=response_text))
        db.commit()

        # 6. Translate response back for the UI
        translated_body = translate_text(response_text, "eng_Latn", nllb_src_lang) if nllb_src_lang != "eng_Latn" else response_text
        
        final_ui_text = f"Ticket #{new_ticket.id} Created.\nCategory: {category_val}\nPriority: {priority_val}\n\n{translated_body}"
        
        return {"reply": final_ui_text}
        
    except Exception as e:
        return {"reply": f"System Error: {str(e)}"}
    
@app.get("/tickets/{employee_id}")
def get_user_tickets(employee_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == employee_id).first()
    if not user:
        return {"tickets": []}
    
    # Fetch all tickets for this user, newest first
    user_tickets = db.query(models.Ticket).filter(models.Ticket.user_id == user.id).order_by(models.Ticket.created_at.desc()).all()
    
    tickets_list = []
    for t in user_tickets:
        tickets_list.append({
            "id": t.id,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    return {"tickets": tickets_list}