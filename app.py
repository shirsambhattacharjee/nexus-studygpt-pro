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

# Tesseract Executable Local Binary Routing
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Page config
st.set_page_config(
    page_title="Nexus StudyGPT Pro",
    page_icon="Nexus_logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Session state initialization
if "app_theme" not in st.session_state:
    st.session_state.app_theme = "Dark Mode 🌌"

if "goal" not in st.session_state:
    st.session_state.goal = ""

if "pending_goal" not in st.session_state:
    st.session_state.pending_goal = ""    

# ==========================================
# CONFIG & INITIALIZATION
# ==========================================
load_dotenv()
HISTORY_FILE = "history.json"

# Initialize Session State Variables
if "history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.history = json.load(f)
        except Exception:
            st.session_state.history = []
    else:
        st.session_state.history = []

if "active_data" not in st.session_state:
    st.session_state.active_data = None

if "quiz_scores" not in st.session_state:
    st.session_state.quiz_scores = {}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

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
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def clear_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
    st.session_state.history = []
    st.session_state.active_data = None
    st.rerun()

# ==========================================
# API SETUP & INTUITIVE MODEL ROUTING
# ==========================================
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

# ==========================================
# SAFETY FILTER
# ==========================================
BLOCKED_WORDS = {"bomb", "weapon", "hack", "malware"}

def is_safe(text):
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    return not any(word in BLOCKED_WORDS for word in words)

# ==========================================
# AGENT CORE ORCHESTRATOR WITH RETRY & LIMIT CONTROL
# ==========================================
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

# ==========================================
# ADVANCED THEMING & UI DESIGN (CUSTOM CSS)
# ==========================================
st.markdown("""
<style>
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
.hero-container{
    text-align:center;
    padding-top:10px;
    padding-bottom:25px;
}
.hero-title{
    font-size:clamp(70px,8vw,120px);
    font-weight:900;
    line-height:1;
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

/* ==========================================
   SIDEBAR READABILITY & CLEANUP FIXES
   ========================================== */
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

# ==========================================
# SIDEBAR NAVIGATION & HISTORY
# ==========================================
with st.sidebar:
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

# ==========================================
# MAIN LAYOUT
# ==========================================
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

# ==========================================
# ENGINE PIPELINE EXECUTION
# ==========================================

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
            You are a premier world-class educator. Compile high-yield comprehensive study notes and a short data facts summary for the topic or raw data given by user: '{search_term}'.
            Target Academic Baseline Profile: {level}.
            Special Guideline: {level_instruction}

            IMPORTANT OUTPUT RULE:

            Only include sections that are relevant to the topic.
            Never create empty sections.
            Never write:
            "Not Applicable"
            "Not Relevant"
            "This section is not applicable"
            or similar placeholders.

            If a section is not relevant to the topic, completely omit that section.
            
            CRITICAL REQUIREMENT: If the provided context contains 'Student document text', you must base your explanations, definitions, and data core strictly on that text. Do not invent details outside of it, but you can enhance technical clarity using global knowledge.

            Format your entire output strictly matching this schema separated by the delimiter '===END_FACTS===' without any extra sentences:
            List exactly 15 distinct, high-density bullet points or formula sets for quick revision.
            ===END_FACTS===
            # 1. Introduction & Core Concept
            Provide an extremely exhaustive, detailed introduction and core background of the topic here. Write long, comprehensive and clear explanatory paragraphs to fully unpack the topic. Do not summarize briefly.
            
            # 2. Key Definitions & Specifications
            Provide comprehensive definitions, core parameters, sub-topics, variants, and standard technical descriptions in detail.
            
            # 3. Formulas, Rules & Working Matrix
            List all essential formulas, mathematical derivations, architecture layouts, or processing rules clearly with rich explanations.
            
            # 4. Step-by-Step Solved Examples
            Provide multiple practical solved examples using real-world scenarios.

            For each example, strictly include:

            Problem:
            Describe a realistic problem statement.

            Step-by-step solution:
            Explain every step clearly and logically.

            Final answer:
            Give the final result separately.

            Common mistakes:
            List common errors students make while solving this type of problem.

            Provide at least 3 detailed examples.

            # 5. Programming Implementation

            IMPORTANT:

            Only generate this section if the topic is directly related to Computer Science, Programming, Data Structures, Algorithms, DBMS, Operating Systems, Computer Networks, Artificial Intelligence, Machine Learning, Software Engineering, Python, C, C++, Java, or JavaScript.

            For all other topics, completely omit this section and continue directly with the next relevant content.

            Never write:
            - This section is not applicable
            - Not relevant
            - N/A
            - Any placeholder message

            This section must include:

            1. Concept Overview
               - Brief explanation of the implementation approach.

            2. Well-Commented Code Examples
               - Use the most suitable language for the topic.
               - Provide beginner-friendly and properly commented code.
               - For Data Structures and Algorithms topics, ALWAYS provide both:
                 - C Implementation
                 - Python Implementation

            3. Code Explanation
               - Explain important functions, variables, and logic step-by-step.

            4. Time and Space Complexity Analysis
               - Time Complexity
               - Space Complexity
               - Best, Average, and Worst Case (if applicable)

            5. Example Input and Output
               - Show sample input and expected output.

            6. Dry Run
               - Demonstrate the execution of the code step-by-step using sample data.

            7. Real-World Applications
               - Explain where the concept is used in practical software systems.

            8. Common Mistakes
               - List common coding and logical errors students make.

            9. Interview Preparation
               - Include at least 5 important interview questions with short answers.

            10. Exam & Placement Focus

            Include:

            - Most important university exam questions
            - Frequently asked coding interview questions
            - Common viva questions
            - Top 5 revision points

            For Data Structures and Algorithms topics, this section is mandatory and must be detailed.
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
            Return ONLY a valid JSON object matching this schema exactly. No extra characters or wrappers.

            {{
              "questions":[
                {{
                  "q":"Question text?",
                  "options":["Option A","Option B","Option C","Option D"],
                  "ans":"A"
                }}
              ]
            }}
            Ensure exactly 8 question objects are built.
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
                f"Generate exactly 10 high-yield revision flashcards targeting core parameters or solving rules for '{search_term}'. Structure each item clearly with Q: and A: markers. Example formatting:\nQ: What is X?\nA: X is Y.",
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

# ==========================================
# INTERACTIVE DATA PRESENTATION LAYER
# ==========================================
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
                        <p style="margin-bottom: 12px; font-size: 1.1rem; color: #ffffff;">
                            <b style="color: #38bdf8;">Question:</b> {q_clean}
                        </p>
                        <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08);">
                            <p style="margin-bottom: 0; color: #cbd5e1; font-size: 1.05rem; line-height: 1.5;">
                               <b style="color: #34d399; display: block; margin-bottom: 4px;">Answer:</b>{a_clean}
                            </p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    card_counter += 1
        else:
            st.info("No active flashcard repository parsed for this topic.")

    with tab4:
        st.subheader("📊 Learning Analytics")
        if st.session_state.history:
            topics_list = [item["topic"] for item in st.session_state.history]
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Topics Studied", len(topics_list))
            with col_m2:
                if data['topic'] in st.session_state.quiz_scores:
                    st.metric("Latest Quiz Score", f"{st.session_state.quiz_scores[data['topic']]}/8")
                else:
                    st.metric("Latest Quiz Score", "N/A")
            st.markdown("#### Topic Frequency Distribution Chart")
            df = pd.DataFrame({"Topics": topics_list})
            st.bar_chart(df["Topics"].value_counts())
        else:
            st.info("No compiled metrics data captured to display.")



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
