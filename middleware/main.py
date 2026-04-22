from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from langdetect import detect
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

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
    "hi": "hin_Deva", # Hindi
    "mr": "mar_Deva", # Marathi
    "bn": "ben_Beng", # Bengali
    "en": "eng_Latn"  # English
}

class ChatRequest(BaseModel):
    message: str

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
    if src_lang == tgt_lang:
        return text
    
    # NLLB expects the source language to be explicitly set in the tokenizer
    tokenizer.src_lang = src_lang
    inputs = tokenizer(text, return_tensors="pt")
    
    # NLLB expects the target language token ID to be passed directly
    tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)
    
    translated_tokens = translator_model.generate(
        **inputs, forced_bos_token_id=tgt_lang_id, max_length=200
    )
    return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]


@app.post("/chat")
def chat_with_bot(request: ChatRequest):
    original_text = request.message
    
    # 1. Detect Language with a fallback safety net
    try:
        detected_lang = detect(original_text)
        print(f"DEBUG - Detected Language Code: {detected_lang}")
        nllb_src_lang = LANG_MAP.get(detected_lang, "eng_Latn")
    except:
        nllb_src_lang = "eng_Latn"

    # 2. Translate User Input to English
    english_input = translate_text(original_text, nllb_src_lang, "eng_Latn") if nllb_src_lang != "eng_Latn" else original_text
    print(f"DEBUG - Translated to AI: {english_input}")

    # 3. Process with AI Logic
    payload = {
        "model": "phi3",
        "prompt": f"{SYSTEM_PROMPT}\n\nEmployee: {english_input}\nChatbot:",
        "stream": False,
        "options": {
            "stop": ["Employee:", "\n\nEmployee:", "User:"]
        }
    }
    
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        bot_english_reply = response.json().get("response", "Error generating response.")
        
        # 4. Parse the output to ONLY translate the "Response:" part
        lines = bot_english_reply.strip().split('\n')
        category_line = "Category: Unknown"
        priority_line = "Priority: Unknown"
        response_text = bot_english_reply 
        
        for line in lines:
            if line.startswith("Category:"): category_line = line
            elif line.startswith("Priority:"): priority_line = line
            elif line.startswith("Response:"): response_text = line.replace("Response:", "").strip()

        # 5. Translate just the response body back to the regional language
        translated_body = translate_text(response_text, "eng_Latn", nllb_src_lang) if nllb_src_lang != "eng_Latn" else response_text
        
        # 6. Reconstruct the final UI output
        final_ui_text = f"{category_line}\n{priority_line}\nResponse: {translated_body}"
        
        return {"reply": final_ui_text}
        
    except Exception as e:
        return {"reply": f"System Error: {str(e)}"}