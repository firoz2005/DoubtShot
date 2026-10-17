import json
import streamlit as st 
import requests  # Added for native Telegram API HTTP requests
from google import genai 
from google.genai import types 
from prompts import  SYSTEM_PROMPT, WELCOME_PROMPT,SUMMARY_PROMPT

MODEL_NAME = "gemini-3.8-flash" 
st.set_page_config(page_title="DoubtShot", page_icon=" 🎓 ") 

# Load secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] 
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]  # Updated secret
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

@st.cache_resource 
def get_gemini_client():     
    return genai.Client(api_key=GEMINI_API_KEY) 
     
gemini_client = get_gemini_client() 

def render_message(message):     
    with st.chat_message(message["role"]):         
        if message["kind"] == "text":             
            st.write(message["content"])         
        elif message["kind"] == "image":             
            st.image(message["content"])  
   
def add_message(role, kind, content):     
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})     
    render_message(st.session_state.messages[-1]) 

def ask_gemini(parts):     
    try:         
        return st.session_state.chat.send_message(parts).text     
    except Exception as error:         
        return f"Sorry, something went wrong: {error}"

# Replaced send_whatsapp with send_telegram
def send_telegram(chat_id, user_name, summary):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Format the text with clean Markdown formatting for Telegram
        text_message = f"👋 *Hey {user_name}!* Here is your daily summary:\n\n{summary}"
        
        payload = {
            "chat_id": chat_id,
            "text": text_message,
            "parse_mode": "Markdown"  # Allows bold fonts and clean spacing
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return True, "Success"
        else:
            return False, response.text
    except Exception as error:         
        return False, str(error) 


if "onboarded" not in st.session_state:     
    st.title(" 🎓 DoubtShot - Your AI Learning Assistant")     
    st.write("login to start your learning journey!")

    with st.form("onboarding_form"):         
        name = st.text_input("Your name")
        password = st.text_input("Password", type="password")  # Added password field
        submitted = st.form_submit_button("Let's go 🚀 ")    

    if submitted:         
        if not name.strip():
            st.warning("Please enter your name.")
        else:             
            st.session_state.name = name.strip()
            st.session_state.chat = gemini_client.chats.create(model=MODEL_NAME,config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT))             
            st.session_state.messages = []             
            st.session_state.onboarded = True             
            st.rerun()
     
    st.stop()


header_col, button_col = st.columns([5, 2], vertical_alignment="center")   
with header_col:     
    st.title("🎓 DoubtShot - Your AI Learning Assistant")  
    st.caption("Learn Smarter, Understand Better — Your AI-Powered Learning Companion")


with button_col:     
    send_disabled = len(st.session_state.messages) <= 2     
    # Changed button text and action target
    if st.button(" 📤 Send to Telegram", disabled=send_disabled, use_container_width=True):         
        with st.spinner("Summarizing your day..."): 
             summary = ask_gemini([SUMMARY_PROMPT])         
             success, info = send_telegram(TELEGRAM_CHAT_ID, st.session_state.name, summary)
        if success:             
            st.success("Sent! Check your Telegram 📲 ")         
        else:             
            st.error(f"Couldn't send that: {info}") 

  
st.caption(f"Logged in as {st.session_state.name} - updates go to the configured Telegram chat.")
if not st.session_state.messages:     
    add_message("assistant", "text", WELCOME_PROMPT.format(name=st.session_state.name)) 
else:     
    for message in st.session_state.messages:         
        render_message(message) 

user_input = st.chat_input("Ask a question, or attach a photo of your meal", accept_file=True, file_type=["jpg", "jpeg", "png"])  

if user_input:     
    photo = user_input.files[0] if user_input.files else None     
    text = user_input.text     
    parts = []       
    if photo is not None:         
        photo_bytes = photo.getvalue()         
        add_message("user", "image", photo_bytes)         
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))     
    if text:         
        add_message("user", "text", text)         
        parts.append(text)     
    elif photo is not None:         
        parts.append("What is this meal? Give me the calories and macros.")       
    with st.spinner("Thinking..."):         
        answer = ask_gemini(parts)     
    add_message("assistant", "text", answer)
