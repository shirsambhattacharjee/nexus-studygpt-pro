from langchain_openai import ChatOpenAI
import streamlit as st
import re
import os
import json
from pdf2image import convert_from_bytes  
import io
import docx
import pandas as pd
from dotenv import load_dotenv
from tools import get_live_wiki_details
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from groq import Groq
import time 
import pytesseract
import cv2
import numpy as np
import hashlib

# Load environment variables at the very beginning
load_dotenv()

# Tesseract Executable Local Binary Routing -
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Page config
st.set_page_config(
    page_title="Nexus StudyGPT Pro",
    page_icon="Nexus_logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize Session State Variables for Theme and Goals
if "app_theme" not in st.session_state:
    st.session_state.app_theme = "Dark Mode 🌌"

if "goal" not in st.session_state:
    st.session_state.goal = ""

if "pending_goal" not in st.session_state:
    st.session_state.pending_goal = ""    


# CONFIG & INITIALIZATION (MULTI-USER SETUP)

BASE_HISTORY_FILE = "history_v2.json"
USER_DB_FILE = "users_db.json"

# SECURE CONFIGURATION: Pulling Master Admin Email from Environment/Secrets
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@domain.com").strip().lower()

# Helper function to hash passwords securely
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Load all users database
def load_users():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# Save users database
def save_user(email, password):
    users = load_users()
    users[email] = hash_password(password)
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# Load global multi-user history structure
def load_global_history():
    if os.path.exists(BASE_HISTORY_FILE):
        try:
            with open(BASE_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# Save global multi-user history structure
def save_global_history(all_history):
    with open(BASE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(all_history, f, indent=2)

# Helper function to validate email structure
def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

# User Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

# Global styling injection - NUCLEAR OPTION FOR BOX REMOVING
st.markdown("""
<style>
/* Global Layout Enhancements */
.block-container{
    max-width:1200px;
    padding-top:1rem;
}
.stApp{
    background:
    radial-gradient(circle at 10% 20%,#06b6d4,transparent 25%),
    radial-gradient(circle at 90% 80%,#8b5cf6,transparent 25%),
    radial-gradient(circle at 50% 50%,#2563eb,transparent 40%),
    #050816 !important;
    transition:all .4s ease;
}

/* Dynamic Glassmorphism Auth UI Design */
.auth-wrapper {
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    
}
.auth-title {
    font-size: 32px;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(90deg, #60a5fa, #818cf8, #22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 5px;
    letter-spacing: -0.5px;
}
.auth-subtitle {
    color: #94a3b8;
    text-align: center;
    font-size: 14px;
    margin-bottom: 25px;
}

/* ULTIMATE FIX: Destroying Streamlit Tabs Inner Borders & Ghost Black Boxes */
div[data-testid="stTabs"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stTabs"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0px !important;
    margin: 0px !important;
}
div[data-testid="stTabs"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    padding: 0px !important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
    background-color: transparent !important;
    border: none !important;
    color: #94a3b8 !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
    color: #22d3ee !important;
    border-bottom: 2px solid #22d3ee !important;
}

/* Core Element Custom Layouts */
.hero-container{
    text-align:center;
    padding-top:10px;
    padding-bottom:25px;
}
.hero-title{
    font-size:clamp(50px,6vw,90px);
    font-weight:900;
    line-height:1.1;
    background:linear-gradient(90deg,#60a5fa,#818cf8,#22d3ee);
    background-size:300% 300%;
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    animation:heroGlow 6s ease infinite;
    filter:drop-shadow(0 0 25px rgba(96,165,250,.25));
}
.hero-subtitle{
    color:#cbd5e1;
    font-size:18px;
    margin-top:12px;
    letter-spacing:.6px;
}
.glass-card,
.framer-box{
    background:rgba(15,23,42,.55);
    backdrop-filter:blur(24px);
    border:1px solid rgba(255,255,255,.08);
    border-radius:20px;
    padding:22px;
    transition:.3s ease;
}
.glowing-flashcard{
    background:rgba(15,23,42,.55);
    backdrop-filter:blur(24px);
    border-radius:18px;
    border:1px solid rgba(99,102,241,.25);
    padding:24px !important;
    margin-bottom:18px !important;
    transition: all .3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glowing-flashcard:hover {
    transform: translateY(-4px) scale(1.01);
    border-color: rgba(6, 182, 212, 0.6);
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.3), inset 0 0 15px rgba(99, 102, 241, 0.2);
}
.stTextInput input{
    background:rgba(15,23,42,.60) !important;
    color:white !important;
    border-radius:14px !important;
    border:1px solid rgba(255,255,255,.08) !important;
}
.stSelectbox div[data-baseweb="select"]{
    background:rgba(15,23,42,.60) !important;
    border-radius:14px !important;
}
.stButton button{
    background:linear-gradient(135deg,#6366f1,#06b6d4) !important;
    color:white !important;
    border:none !important;
    border-radius:14px !important;
    font-weight:700 !important;
    transition:.3s ease !important;
}
.stButton button:hover{
    transform:scale(1.03);
    box-shadow:0 0 22px rgba(99,102,241,.40);
}
[data-testid="metric-container"]{
    background:rgba(15,23,42,.45);
    border:1px solid rgba(255,255,255,.06);
    border-radius:18px;
    padding:12px;
    backdrop-filter:blur(18px);
}
section[data-testid="stSidebar"]{
    background:rgba(15,23,42,.45) !important;
    backdrop-filter:blur(24px);
    border-right:1px solid rgba(255,255,255,.05);
}
::-webkit-scrollbar{
    width:8px;
}
::-webkit-scrollbar-thumb{
    background:#6366f1;
    border-radius:20px;
}
@keyframes heroGlow{
    0%{ background-position:0% 50%; }
    50%{ background-position:100% 50%; }
    100%{ background-position:0% 50%; }
}

[data-testid="stSidebar"] {
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] .stButton button {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    text-align: left !important;
    padding: 8px 12px !important;
    color: #f1f5f9 !important;
    border-radius: 10px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    display: block !important;
    width: 100% !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(99, 102, 241, 0.2) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    box-shadow: none !important;
    transform: none !important;
}

div[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button {
    background: rgba(239, 68, 68, 0.15) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    color: #ef4444 !important;
    text-align: center !important;
    padding: 8px 0px !important;
}

div[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button:hover {
    background: rgba(239, 68, 68, 0.3) !important;
    border-color: #ef4444 !important;
}
            
@media (max-width: 768px){
    .hero-title{
        font-size:40px !important;
    }
    .hero-subtitle{
        font-size:14px !important;
    }
    .block-container{
        padding-left:10px !important;
        padding-right:10px !important;
    }
    .glass-card,
    .framer-box,
    .glowing-flashcard{
        padding:12px !important;
        border-radius:12px !important;
    }
    h1,h2,h3{
        font-size:90% !important;
    }
    p{
        font-size:14px !important;
    }
}        

</style>
""", unsafe_allow_html=True)

# MULTI-USER LOGIN AND REGISTER INTERFACE (CLEANED)

if not st.session_state.authenticated:
    st.markdown("<div style='margin-top: 5%;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;' class='hero-title'>⚡ NEXUS StudyGPT Pro</h1>", unsafe_allow_html=True)
    
    # Unified Premium Glassmorphic Container
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)
    st.markdown('<p class="auth-title">Cognitive Gateway Portal</p>', unsafe_allow_html=True)
    st.markdown('<p class="auth-subtitle">Verify cryptographic credentials to spin up neural engines</p>', unsafe_allow_html=True)
    
    auth_mode = st.tabs(["🔒 Secure Authorization", "🚀 Deploy New Account"])
    
    with auth_mode[0]:
        login_user = st.text_input("📬 Email Identifier Address", placeholder="username@domain.com", key="login_user_input")
        login_pass = st.text_input("🔑 Cryptographic Password Token", type="password", placeholder="••••••••", key="login_pass_input")
        if st.button("Initialize Quantum Session Layer", use_container_width=True):
            users = load_users()
            clean_email = login_user.strip().lower()
            if clean_email in users and users[clean_email] == hash_password(login_pass):
                st.session_state.authenticated = True
                st.session_state.username = clean_email
                global_history = load_global_history()
                st.session_state.history = global_history.get(clean_email, [])
                st.success(f"Access granted. Synchronizing node profile...")
                st.rerun()
            else:
                st.error("Invalid credentials sequence or configuration profile mapping.")
                
    with auth_mode[1]:
        reg_user = st.text_input("📬 Registration Email Account", placeholder="user@domain.com", key="reg_user_input")
        reg_pass = st.text_input("🔑 Setup Secure Password Sequence", type="password", placeholder="Minimum 6 characters", key="reg_pass_input")
        reg_confirm = st.text_input("🔄 Confirm Cryptographic Sequence", type="password", placeholder="Repeat matching password", key="reg_confirm_input")
        if st.button("Compile Structural Node Profile", use_container_width=True):
            users = load_users()
            clean_reg_email = reg_user.strip().lower()
            if not clean_reg_email or not reg_pass.strip():
                st.error("Data parameters missing inside transaction script.")
            elif not is_valid_email(clean_reg_email):
                st.error("Invalid structural configuration layout inside your Mail ID.")
            elif clean_reg_email in users:
                st.error("Identity matrix collision: Email already verified in master table.")
            elif reg_pass != reg_confirm:
                st.error("Cryptographic token matching validation failed.")
            else:
                save_user(clean_reg_email, reg_pass)
                st.success("Identity compiled! Swap tabs to initialize standard session authorization.")
                
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Re-verify and match current logged user dynamic reference constraints
current_user = st.session_state.username
global_history = load_global_history()

if "history" not in st.session_state or not st.session_state.history:
    st.session_state.history = global_history.get(current_user, [])

if "active_data" not in st.session_state:
    st.session_state.active_data = None

if "quiz_scores" not in st.session_state:
    st.session_state.quiz_scores = {}

# HELPER FUNCTIONS

def extract_file_content(uploaded_file):
    text = ""
    if uploaded_file.type == "application/pdf":
        with st.spinner("🔮 OCR Engine running with High-Resolution Binary Enhancement..."):
            try:
                file_bytes = uploaded_file.read()
                try:
                    images = convert_from_bytes(file_bytes, dpi=300)
                except Exception:
                    images = convert_from_bytes(file_bytes, dpi=300, poppler_path=r"C:\poppler\Library\bin")
                
                for i, image in enumerate(images):
                    open_cv_image = np.array(image.convert('RGB'))
                    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    page_text = pytesseract.image_to_string(thresh, lang='eng', config='--psm 6')
                    if page_text.strip():
                        text += f"--- Page {i+1} ---\n" + page_text + "\n"
            except Exception as e:
                st.error(f"🚨 OCR Processing Error: {e}")
                text = ""
                
    elif uploaded_file.type.endswith("wordprocessingml.document"):
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.read().decode("utf-8")
    return text

def create_pdf(topic, notes):
    filename = f"{topic.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = [
        Paragraph(f"<b>{topic}</b>", styles["Title"]),
        Paragraph(notes.replace("\n", "<br/>"), styles["BodyText"])
    ]
    doc.build(content)
    return filename

def save_history(history):
    all_hist = load_global_history()
    all_hist[st.session_state.username] = history
    save_global_history(all_hist)

def clear_history():
    all_hist = load_global_history()
    all_hist[st.session_state.username] = []
    save_global_history(all_hist)
    st.session_state.history = []
    st.session_state.active_data = None
    st.rerun()


# API SETUP & INTUITIVE MODEL ROUTING

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("Missing GROQ_API_KEY in .env file")
    st.stop()

client_fast = ChatOpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.1-8b-instant",
    temperature=0.2,
    timeout=20.0,
    max_retries=3
)

client_smart = ChatOpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.3-70b-versatile",
    temperature=0.2,
)

groq_raw_client = Groq(api_key=api_key)


# SAFETY FILTER

BLOCKED_WORDS = {"bomb", "weapon", "hack", "malware"}

def is_safe(text):
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    return not any(word in BLOCKED_WORDS for word in words)


# AGENT CORE ORCHESTRATOR WITH RETRY & LIMIT CONTROL

def run_agent(role, instruction, target_input, retries=4, initial_delay=4):
    if role in ["EXPERT_WRITER", "QUIZ_GENERATOR"]:
        selected_client = client_smart
    else:
        selected_client = client_fast
    delay = initial_delay
    for attempt in range(retries):
        try:
            response = selected_client.invoke([
                {"role": "system", "content": f"You are the {role}. {instruction}"},
                {"role": "user", "content": target_input[:4000]}
            ])
            return response.content

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg or "connection" in error_msg or "timeout" in error_msg or "overloaded" in error_msg:
                if attempt < retries - 1:
                    st.warning(f"⚠️ API/Network Congestion on {role}. Retrying in {delay}s... (Attempt {attempt+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2  
                    continue
                else:
                    st.error(f"🚨 Network link or API Token window completely exhausted for {role}.")
                    return f"Error: Connection/Rate Outage for {role}. Please attempt compilation again."
            raise e


# SIDEBAR NAVIGATION & HISTORY

with st.sidebar:
    st.markdown(f"📬 Active Node: **{st.session_state.username}**")
    if st.button("🚪 Logout Matrix Workspace", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.history = []
        st.session_state.active_data = None
        st.rerun()
        
    st.markdown("---")
    
    # MASTER ADMIN BACKDOOR ACCESS PANEL CONTROL
    if st.session_state.username == ADMIN_EMAIL and ADMIN_EMAIL != "admin@domain.com":
        with st.expander("👑 Admin Control Panel", expanded=False):
            st.caption("Active Central Logs Tracking System")
            all_users_registered = load_users()
            all_centralized_history = load_global_history()
            
            st.markdown(f"**Total Registered Nodes:** `{len(all_users_registered)}`")
            selected_user_node = st.selectbox("Inspect Active User Data", list(all_users_registered.keys()))
            
            if selected_user_node:
                user_nodes_history = all_centralized_history.get(selected_user_node, [])
                st.markdown(f"**Cached Log Entities:** `{len(user_nodes_history)}`")
                if user_nodes_history:
                    for tracked_idx, tracked_item in enumerate(user_nodes_history):
                        st.text_area(
                            f"Topic Log {tracked_idx + 1}: {tracked_item.get('topic')}", 
                            value=tracked_item.get('notes')[:500] + "\n...[Truncated Output Stream]...", 
                            height=120,
                            key=f"admin_track_nodes_{selected_user_node}_{tracked_idx}"
                        )
                else:
                    st.caption("No compiled datasets processed by this specific profile.")
        st.markdown("---")

    st.markdown("### 📜 Recent Compilations")
    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history)):
            real_index = len(st.session_state.history) - 1 - idx
            
            col1, col2 = st.columns([0.82, 0.18])
            
            with col1:
                
                display_name = item['topic'][:18] + "..." if len(item['topic']) > 18 else item['topic']
                if st.button(f"📄 {display_name}", key=f"hist_view_{real_index}", use_container_width=True):
                    st.session_state.active_data = item
                    st.rerun()
            with col2:
                if st.button("✕", key=f"hist_del_{real_index}", help="Delete Entry"):
                    st.session_state.history.pop(real_index)
                    save_history(st.session_state.history)
                    if st.session_state.active_data == item:
                        st.session_state.active_data = None
                    st.rerun()
                    
        st.markdown("---")
        if st.button("🗑️ Clear Workspace History", use_container_width=True):
            clear_history()
    else:
        st.caption("No historical entities cached inside your local environment.")

# MAIN LAYOUT

st.markdown("<h1 style='text-align:center;font-size:72px;font-weight:900;' class='hero-title'>⚡ NEXUS StudyGPT Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;font-size:18px;' class='hero-subtitle'>Framer-grade AI Learning & Research OS</p>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; text-align:center; font-size:1.1rem; margin-bottom:2rem;'>Cognitive Multi-Agent Workflow Engine for Educational Synthesis</p>", unsafe_allow_html=True)

chat_container = st.container()
execute_pipeline = False

with chat_container:
    col_lvl, col_goal = st.columns([1, 3])
    with col_lvl:
        level = st.selectbox("Academic Profile", ["School", "College", "Competitive Exam"])
    with col_goal:
        if st.session_state.pending_goal:
           st.session_state.goal = st.session_state.pending_goal
           st.session_state.pending_goal = ""

        is_doc = st.session_state.goal.startswith("Student document text:\n")
        goal = st.text_input(
            "What do you want to learn today?",
            value="[Uploaded Document Analysis]" if is_doc else st.session_state.goal,
            placeholder="e.g., Deep Neural Networks, Quantitative Aptitude, Quantum Mechanics"
        )
        if not is_doc:
            st.session_state.goal = goal
    
    with st.expander("📂 Attach Documents (Optional context)", expanded=False):
        st.markdown("📂 **Upload Study Material**")
        uploaded_file = st.file_uploader("Upload PDF / TXT / DOCX", type=["pdf","txt","docx"], label_visibility="collapsed")
        if uploaded_file:
            file_text = extract_file_content(uploaded_file)
            if file_text.strip():
                st.success("Document attached successfully!")
                st.session_state.goal = "Student document text:\n" + file_text[:15000]
            else:
                st.error("🚨 No text could be read from this PDF.Is the file okay?")

    manual_deploy = st.button("Launch AI Workflow", type="primary", use_container_width=True)
    if manual_deploy:
        execute_pipeline = True

# ENGINE PIPELINE EXECUTION

if execute_pipeline:
    active_payload = st.session_state.goal.strip()

    if not active_payload:
        st.warning("Execution halted: Input channel empty.")
    elif not is_safe(active_payload):
        st.error("Access Exception: Guardrail Triggered.")
    else:
        with st.status("Initializing High-Speed Multi-Agent Engine...", expanded=True) as status:
            # 1. PLANNER
            status.update(label="🧠 Filtering Topic Targets...")
            
            planner_input = active_payload
            if active_payload.startswith("Student document text:\n"):
                planner_input = active_payload[:1500]
                
            planner_output = run_agent(
                "PLANNER",
                "Identify the specific scientific, historical, or technological core entity from the user raw string. Return ONLY the title clean. No metadata, no framing phrases.",
                planner_input
            )
            search_term = planner_output.strip().strip('"').strip("'")
            if not search_term or len(search_term) > 60 or "error" in search_term.lower():
                search_term = "Document Analysis Topic" if active_payload.startswith("Student document text:\n") else active_payload[:50]
                
            # 2. WIKIPEDIA CORE TOOL
            status.update(label=f"🔍 Extracting online raw records for: '{search_term}'...")
            try:
                live_info = get_live_wiki_details(search_term)
                st.write("Wiki Loaded")
            except Exception as e:
                st.write(f"Wiki Error: {e}")
                live_info = search_term
            
            if active_payload.startswith("Student document text:\n"):
                context_payload = f"{active_payload}\n\n[Additional Reference Context from Web]:\n{live_info}"
            else:
                context_payload = live_info
            
            # 3. COMBINED RESEARCHER & WRITER
            status.update(label="✍️ Executing Contextual Synthesis & Knowledge Formulation...")
            
            level_instruction = ""
            if level == "Competitive Exam":
                level_instruction = "Focus strictly on exam-oriented patterns, high-yield shortcut methods, formulas, problem-solving algorithms, and practical mathematical/logical reasoning frameworks."
            elif level == "College":
                level_instruction = "Provide formal academic explanation with computer science/engineering deep theoretical concepts and structured analytical breakdown."
            else:
                level_instruction = "Provide a simple, highly intuitive layout with basic real-world examples."

            combined_prompt = f"""
            You are a world-class AI educator, examiner, and technical expert.

            Your task is to generate structured, high-quality learning material for the topic:
            '{search_term}'

            Target Academic Level: {level}
            Instruction Style: {level_instruction}

            # 🚨 CRITICAL OUTPUT RULES (MUST FOLLOW STRICTLY)

            1. Only include sections relevant to the topic.
            2. NEVER write:
               - "Not Applicable"
               - "Not Relevant"
               - "N/A"
               - empty placeholders
            3. If something is not relevant → completely OMIT it.
            4. Do NOT add any extra commentary outside the format.
            5. Maintain deep educational quality (exam + conceptual clarity).

            
             📌 OUTPUT FORMAT (STRICT ORDER)
            

            First output MUST be:

            List exactly 15 high-density bullet points for quick revision.

            Then write:

            ===END_FACTS===

            Then continue sections:

            # 1. Introduction & Core Concept
            - Deep, detailed explanation
            - Include real-world intuition and background
            - Expand concepts fully (no short summaries)

            # 2. Key Definitions & Specifications
            - All important terms clearly defined
            - Include classifications, types, parameters if applicable

            # 3. Formulas / Rules / Core Mechanism
            - Only if applicable to topic
            - Include formulas, logic, architecture, or workflows
            - Explain meaning of each formula/part briefly

            # 4. Step-by-Step Solved Examples
            - MUST include at least 3 examples (if applicable)
            Each example must contain:
              Problem
              Step-by-step solution
              Final Answer
              Common Mistakes

            🧠 SMART PROGRAMMING LOGIC (VERY IMPORTANT)
            

            If AND ONLY IF the topic is related to:
            - Programming (C, C++, Python, Java, JS)
            - Data Structures
            - Algorithms
            - DBMS, OS, CN
            - AI / ML / Software Engineering (technical)

            THEN include:

            # 5. Programming Implementation

            Include:
            1. Concept Overview (implementation idea)
            2. Code in C (mandatory for DSA)
            3. Code in Python (mandatory for DSA)
            4. Explanation of logic step-by-step
            5. Time & Space Complexity
            6. Dry Run
            7. Real-world use cases
            8. Common coding mistakes
            9. Interview questions (minimum 5)
            10. Exam + Viva important points

            ⚠️ If topic is NOT programming related:
            → DO NOT generate this section at all (no placeholders, no "not applicable")

            
            🎯 OUTPUT QUALITY RULES

            - Competitive exam topics → focus on shortcuts, formulas, tricks, exam patterns
            - College topics → deep theoretical + structured explanation
            - Basic topics → simple explanation with examples
            - Always prioritize clarity + correctness + exam usefulness

            Now generate the response exactly in the required format.
            """
            st.write("Starting Expert Writer...")
            combined_response = run_agent("EXPERT_WRITER", combined_prompt, context_payload[:3800])
            st.write("Expert Writer Completed")
            
            if "Error:" in combined_response:
                st.error(combined_response)
                st.stop()
            
            split_match = re.split(r"(?:===|###)END_FACTS(?:===|###)?", combined_response)
            if len(split_match) > 1:
                facts = split_match[0].strip()
                draft = split_match[1].strip()
                draft = re.sub(r"^.*?(\#\s*1\.)", r"\1", draft, flags=re.DOTALL).strip()
            else:
                facts = "Facts compilation processing exception."
                draft = combined_response.strip()

            # 4. EVALUATOR
            status.update(label="🧐 Running Quality Control Audit Matrix...")
            evaluation = run_agent(
                "EVALUATOR",
                "Audit the accuracy and clarity metrics of the text. Format output text identically to:\nScore: X/10\nFeedback: <Sentence description summary>",
                draft
            )
            
            # 5. DYNAMIC MCQs
            status.update(label="📝 Generating Core Concept-Focused MCQ Diagnostic Dataset...")
            quiz_prompt = f"""
            Generate EXACTLY 8 MCQs on {search_term} based on this context: {draft[:2000]}.
            Return ONLY a valid JSON object matching this schema exactly.
            {{
              "questions":[
                {{
                  "q":"Question text?",
                  "options":["Option A","Option B","Option C","Option D"],
                  "ans":"A"
                }}
              ]
            }}
            """
            try:
                response = groq_raw_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": quiz_prompt}]
                )
                quiz_raw = response.choices[0].message.content
            except Exception as e:
                st.error(f"Quiz Generation Error: {e}")
                quiz_raw = '{ "questions": [] }'
            
            # 6. FLASHCARDS
            status.update(label="🧠 Formatting Visual Memory Flashcards...")
            flashcards_raw = run_agent(
                "FLASHCARD_GENERATOR",
                f"Generate exactly 10 high-yield revision flashcards targeting core parameters or solving rules for '{search_term}'. Structure each item clearly with Q: and A: markers.",
                draft
            )
            
            # SAVE ARTIFACT INTO CACHE
            new_item = {
                "topic": search_term,
                "level": level,
                "facts": facts.strip(),
                "evaluation": evaluation,
                "notes": draft.strip(),
                "quiz": quiz_raw,
                "flashcards": flashcards_raw
            }
            st.session_state.history.append(new_item)
            save_history(st.session_state.history)
            st.session_state.active_data = new_item
            
            status.update(label="⚡ Pipeline Tasks Execution Terminated Successfully", state="complete")
        st.rerun()


# INTERACTIVE DATA PRESENTATION LAYER

if st.session_state.active_data:
    data = st.session_state.active_data
    
    st.write("---")
    st.markdown(f"## 📊 Active Entity Workspace Analysis: <span style='color:#38bdf8;'>{data['topic']}</span>", unsafe_allow_html=True)
    
    col_f, col_q, col_fl, col_lv = st.columns(4)
    with col_f:
        st.metric("Retrieved Core Facts", "15 Data Nodes")
    with col_q:
        quiz_count = 0
        try:
            quiz_count = len(json.loads(data["quiz"])["questions"])
        except:
            pass
        st.metric("Parsed MCQs", f"{quiz_count} Questions")
    with col_fl:
        q_matches = re.findall(r"Q:\s*(.*?)(?=A:|\n\n|Q:|$)", data.get("flashcards", ""), re.DOTALL)
        st.metric("Revision Flashcards", f"{len(q_matches) if q_matches else 10} Units")
    with col_lv:
        st.metric("Academic Configuration Profile", data.get("level", "Standard"))
        
    with st.expander("📥 Export Document Asset Manager", expanded=False):
        if st.button("⚡ Generate PDF Report Data", key="pdf_generation_trigger_btn", use_container_width=True):
            pdf_filename = create_pdf(data["topic"], data["notes"])
            with open(pdf_filename, "rb") as f:
                st.download_button(
                    label="📥 Click here to download ready PDF Asset",
                    data=f,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
        
    with st.expander("🔬 Core System Engine Execution Logs", expanded=False):
        st.markdown("### 📊 Researcher Facts Database")
        st.code(data.get("facts", "No data logs found."))
        st.markdown("### 🧐 Audit Evaluation Log")
        st.text(data.get("evaluation", "No evaluation summary logged."))
        
    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 Verified Knowledge Dossier",
        "🧠 Interactive Diagnostic Assessment",
        "⚡ Active Memory Flashcards",
        "📊 Analytics Dashboard"
    ])

    with tab1:
        if "Error:" in data['notes']:
            st.error(data['notes'])
        else:
            st.markdown(data['notes'])

    with tab2:
        st.markdown("### 🎯 Dynamic Diagnostic Assessment Module")
        raw_json_str = data.get("quiz", "{}")
        parsed_quiz = None
        
        try:
            clean_str = re.sub(r"^```(json)?", "", raw_json_str.strip())
            clean_str = re.sub(r"```$", "", clean_str).strip()
            parsed_quiz = json.loads(clean_str)
        except Exception:
            pass

        if parsed_quiz and "questions" in parsed_quiz and parsed_quiz["questions"]:
            questions_list = parsed_quiz["questions"]
            selections = []
            
            for i, q_item in enumerate(questions_list):
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom: 18px; border-left: 4px solid #6366f1;">
                    <p style="font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; color: #ffffff;">Q{i+1}: {q_item.get('q', 'Question Item Schema')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                options = q_item.get("options", [])
                if not isinstance(options, list): options = []
                while len(options) < 4: options.append(f"Option {len(options)+1}")

                option_map = {"A": options[0], "B": options[1], "C": options[2], "D": options[3]}
                user_sel = st.radio(f"Select Answer for Q{i+1}:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}. {option_map[x]}", key=f"dynamic_quiz_rad_{i}")
                selections.append(user_sel)
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            
            if st.button("Audit Evaluation Matrix Scores", key="audit_btn"):
                correct_answers = [q.get("ans", "A").upper().strip() for q in questions_list]
                score_metrics = sum(1 for u, c in zip(selections, correct_answers) if u == c)
                st.session_state.quiz_scores[data['topic']] = score_metrics
                if score_metrics >= len(questions_list)/2:
                    st.success(f"🏆 Review Passed: Achieved {score_metrics}/{len(questions_list)} correct answers!")
                else:
                    st.error(f"📉 Optimization Suggested: Score {score_metrics}/{len(questions_list)}. Re-evaluate structural facts.")
        else:
            st.info("No active quiz diagnostic dataset found for this topic.")

    with tab3:
        st.markdown("### ⚡ Rapid Retrieval Flashcards")
        flashcards_text = data.get("flashcards", "")
        
        questions_found = re.findall(r"Q:\s*(.*?)(?=A:|\n\n|Q:|$)", flashcards_text, re.DOTALL)
        answers_found = re.findall(r"A:\s*(.*?)(?=Q:|\n\n|A:|$)", flashcards_text, re.DOTALL)
        
        card_counter = 1
        if questions_found and answers_found:
            for q_part, a_part in zip(questions_found, answers_found):
                q_clean = q_part.strip()
                a_clean = a_part.strip()
                if q_clean and a_clean:
                    st.markdown(f"""
                    <div class="glowing-flashcard" style="padding:24px;">
                        <h5 style="color: #818cf8; margin-top: 0; font-weight: 700;">⚡ Flashcard {card_counter}</h5>
                        <p style="margin-bottom: 12px; font-size: 1.1rem; color: #ffffff;"><b style="color: #38bdf8;">Q:</b> {q_clean}</p>
                        <p style="margin-top: 4px; font-size: 1rem; color: #cbd5e1;"><b style="color: #34d399;">A:</b> {a_clean}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    card_counter += 1
        else:
            st.info("No structured flashcards found.")
            
    with tab4:
        st.markdown("### 📊 Learning Diagnostics & Engagement Metrics")
        if data['topic'] in st.session_state.quiz_scores:
            latest_score = st.session_state.quiz_scores[data['topic']]
            st.metric(label="Latest Diagnostic Quiz Performance", value=f"{latest_score} / 8 Correct")
            st.progress(latest_score / 8)
        else:
            st.info("Pass the diagnostic test inside Tab 2 to view performance analytics metrics.")



st.markdown("""
<div style="
margin-top:60px;
padding:25px;
text-align:center;
border-top:1px solid rgba(255,255,255,0.08);
background:rgba(15,23,42,.25);
backdrop-filter:blur(10px);
border-radius:15px;
">

<h4 style="
margin-bottom:8px;
font-weight:800;
font-size:24px;
">
🧠
<span style="
background:linear-gradient(90deg,#60a5fa,#818cf8,#22d3ee);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
">
Nexus Cognitive Engine
</span>
</h4>

<p style="color:#cbd5e1;font-size:15px;margin-bottom:8px;">
Designed & Developed by <b>Shirsam Bhattacharjee</b>
</p>

<p style="color:#94a3b8;font-size:13px;margin-bottom:8px;">
AI-Powered Learning & Research Platform
</p>

<p style="color:#64748b;font-size:12px;">
© 2026 Shirsam Bhattacharjee. All Rights Reserved.
</p>

</div>
""", unsafe_allow_html=True)
