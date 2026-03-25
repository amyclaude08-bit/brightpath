"""
BrightPath Training — Streamlit Operations Dashboard
-----------------------------------------------------
Run:  streamlit run app.py
Requires: pip install anthropic streamlit
"""

import os
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
import anthropic

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BrightPath Operations",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Hide default Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main background */
.stApp { background-color: #0e0f11; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #16181c;
    border-right: 1px solid #2a2d35;
}
section[data-testid="stSidebar"] * { color: #e8eaf0 !important; }

/* Cards */
.bp-card {
    background: #16181c;
    border: 1px solid #2a2d35;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.bp-card-accent {
    background: rgba(232,255,107,0.05);
    border: 1px solid #e8ff6b;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.bp-card-green {
    background: rgba(107,255,184,0.05);
    border: 1px solid #6bffb8;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.bp-card-red {
    background: rgba(255,107,107,0.05);
    border: 1px solid #ff6b6b;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.bp-card-blue {
    background: rgba(116,185,255,0.05);
    border: 1px solid #74b9ff;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}

/* Tags */
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    margin-right: 6px;
}
.tag-sales     { background: rgba(107,255,184,0.15); color: #6bffb8; }
.tag-cs        { background: rgba(116,185,255,0.15); color: #74b9ff; }
.tag-escalation{ background: rgba(255,107,157,0.15); color: #ff6b9d; }
.tag-high      { background: rgba(255,107,107,0.15); color: #ff6b6b; }
.tag-medium    { background: rgba(255,169,77,0.15);  color: #ffa94d; }
.tag-low       { background: rgba(107,255,184,0.15); color: #6bffb8; }
.tag-positive  { background: rgba(107,255,184,0.15); color: #6bffb8; }
.tag-negative  { background: rgba(255,107,107,0.15); color: #ff6b6b; }
.tag-hostile   { background: rgba(255,107,157,0.15); color: #ff6b9d; }
.tag-neutral   { background: rgba(139,143,158,0.15); color: #8b8f9e; }

/* Agent step */
.agent-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid #2a2d35;
}
.agent-step:last-child { border-bottom: none; }
.step-num {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #e8ff6b;
    color: #0e0f11;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
}
.step-num-done {
    background: #6bffb8;
}

/* Metric cards */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}
.metric-card {
    background: #16181c;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    padding: 14px 16px;
    text-align: center;
}
.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    color: #e8ff6b;
    line-height: 1;
}
.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #555a6b;
    margin-top: 4px;
}

/* Telegram box */
.telegram-box {
    background: #17212b;
    border: 1px solid #2b5278;
    border-radius: 12px;
    padding: 16px 18px;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    color: #e8eaf0;
    line-height: 1.6;
    position: relative;
}
.telegram-box::before {
    content: '✈ Telegram';
    display: block;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #2b5278;
    margin-bottom: 8px;
}

/* Draft response */
.draft-box {
    background: #16181c;
    border-left: 3px solid #6bffb8;
    padding: 14px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    line-height: 1.7;
    color: #c8cad4;
    white-space: pre-wrap;
}

/* Flag chips */
.flag-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    background: rgba(255,107,157,0.15);
    color: #ff6b9d;
    margin: 2px;
    border: 1px solid rgba(255,107,157,0.3);
}

/* Section headers */
.section-header {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #555a6b;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a2d35;
}

/* Memory viewer */
.memory-file {
    background: #13151a;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    padding: 14px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #8b8f9e;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
    line-height: 1.6;
}

/* Action needed banner */
.action-banner {
    background: rgba(255,107,107,0.1);
    border: 1px solid #ff6b6b;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ff6b6b;
    font-size: 13px;
    margin-top: 10px;
}
.value-banner {
    background: rgba(107,255,184,0.1);
    border: 1px solid #6bffb8;
    border-radius: 8px;
    padding: 12px 16px;
    color: #6bffb8;
    font-size: 13px;
    margin-top: 10px;
}
.risk-banner {
    background: rgba(255,169,77,0.1);
    border: 1px solid #ffa94d;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ffa94d;
    font-size: 13px;
    margin-top: 10px;
}

/* Headings */
h1, h2, h3 { color: #e8eaf0 !important; font-family: 'Syne', sans-serif !important; }
p, li, span { color: #c8cad4; }
label { color: #8b8f9e !important; }

/* Buttons */
.stButton > button {
    background: #e8ff6b !important;
    color: #0e0f11 !important;
    border: none !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #f0ff80 !important;
    transform: translateY(-1px) !important;
}

/* Selectbox / text input */
.stSelectbox > div > div,
.stTextArea > div > div > textarea {
    background: #1e2127 !important;
    border: 1px solid #2a2d35 !important;
    color: #e8eaf0 !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: #e8ff6b !important;
    box-shadow: none !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #16181c;
    border-bottom: 1px solid #2a2d35;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #555a6b !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    padding: 10px 18px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #e8ff6b !important;
    border-bottom-color: #e8ff6b !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #0e0f11 !important;
    padding: 20px 0 !important;
}

/* Spinner */
.stSpinner > div { border-top-color: #e8ff6b !important; }

/* Dataframe */
.stDataFrame { background: #16181c; }

/* Divider */
hr { border-color: #2a2d35 !important; }
</style>
""", unsafe_allow_html=True)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
AGENTS = BASE / "agents"
MEMORY = BASE / "memory"
DATA   = BASE / "data"
DB     = BASE / "brightpath.db"

# ── Anthropic ──────────────────────────────────────────────────────────────
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL   = "claude-sonnet-4-5"

# ── Scenarios ──────────────────────────────────────────────────────────────
SCENARIOS = {
    "1 — New sales lead":
        "Hi, we're looking for leadership training for 30 managers in May. Can you send pricing? We're comparing a few providers. — Marcus, Operations Director, Pinnacle Group",
    "2 — Customer booking change":
        "Hi, I need to move my workshop booking from April to June. I'm booked onto the 8th April Presentation Skills session. Thanks, James Cooper",
    "3 — Angry customer complaint":
        "This is absolutely unacceptable. I attended your Managing People workshop last month and the trainer was unprepared and the materials were out of date. I want a full refund and an explanation. — Linda Okafor",
    "4 — VIP upsell (Nexus Digital)":
        "Hi, it's Dan from Nexus Digital. We're really happy with the partnership so far. Any chance we could add some 1:1 coaching for three of our senior managers this quarter?",
    "5 — Duplicate/returning lead":
        "Hello, I'm reaching out from Acme Logistics. We're interested in corporate training for our management team — about 25 people. Can you send information? — Sarah Miles, HR Director",
    "6 — Multi-request email":
        "Hi, I need to change my booking for next week AND can you resend my invoice as I can't find it AND also — are you planning any resilience workshops this year? Thanks, Tom Nguyen",
    "7 — Cold lead re-engagement":
        "Hi there, Rachel Drummond from Stormfront Media. We spoke a couple of months ago about leadership training. We've finally got budget confirmed. Are you still running programmes?",
    "8 — Competitor price challenge":
        "We've been comparing training providers and Leadership Lab is offering the same course for 20% less. Can you match that price for our team of 15?",
    "9 — Refund — policy edge case":
        "Hi, I booked the April workshop last month but unfortunately I've just been made redundant and can no longer afford it. I know it might be outside your cancellation window but is there any flexibility? — Greg Walsh",
    "10 — Manager daily briefing":
        "Show me a summary of everything open and urgent today. What needs my attention?",
    "— Custom message —": "",
}


# ══════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, message TEXT, category TEXT,
        urgency TEXT, sentiment TEXT,
        triage_out TEXT, agent_out TEXT, briefing TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TEXT, task TEXT, priority TEXT,
        status TEXT DEFAULT 'open', source TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS crm_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, contact TEXT, action TEXT, notes TEXT)""")
    conn.commit(); conn.close()


def log_event(message, triage, agent_result, briefing):
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("""INSERT INTO events
        (timestamp,message,category,urgency,sentiment,triage_out,agent_out,briefing)
        VALUES (?,?,?,?,?,?,?,?)""",
        (datetime.now().isoformat(), message,
         triage.get("category"), triage.get("urgency"), triage.get("sentiment"),
         json.dumps(triage), json.dumps(agent_result), json.dumps(briefing)))
    conn.commit(); conn.close()


def add_task(task_text, priority, source):
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (created,task,priority,source) VALUES (?,?,?,?)",
              (datetime.now().isoformat(), task_text, priority, source))
    conn.commit(); conn.close()


def log_crm(contact, action, notes):
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("INSERT INTO crm_log (timestamp,contact,action,notes) VALUES (?,?,?,?)",
              (datetime.now().isoformat(), contact, action, notes))
    conn.commit(); conn.close()


def get_tasks():
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("SELECT created, task, priority, status FROM tasks ORDER BY created DESC LIMIT 30")
    rows = c.fetchall(); conn.close()
    return rows


def get_events():
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("SELECT timestamp, category, urgency, sentiment, message FROM events ORDER BY timestamp DESC LIMIT 20")
    rows = c.fetchall(); conn.close()
    return rows


def get_counts():
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE status='open'"); open_tasks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM events WHERE urgency='high'"); high = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM crm_log"); crm = c.fetchone()[0]
    conn.close()
    return total, open_tasks, high, crm


# ══════════════════════════════════════════════════════════════════════════
# FILE LOADERS
# ══════════════════════════════════════════════════════════════════════════

def load_file(path):
    if Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return ""

def load_agent(name):
    return load_file(AGENTS / f"{name}.md")

def load_memory():
    files = ["company_context.md", "customer_history.md", "sales_notes.md", "open_tasks.md"]
    combined = []
    for f in files:
        content = load_file(MEMORY / f)
        if content:
            combined.append(f"## {f}\n\n{content}")
    return "\n\n---\n\n".join(combined)

def load_crm():
    path = DATA / "crm.json"
    if path.exists():
        return json.dumps(json.loads(path.read_text()), indent=2)
    return "{}"


# ══════════════════════════════════════════════════════════════════════════
# CLAUDE CALLS
# ══════════════════════════════════════════════════════════════════════════

def call_claude(system_prompt, user_message):
    client = anthropic.Anthropic(api_key=API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def run_triage(message, memory):
    system = f"{load_agent('triage_agent')}\n\n--- MEMORY ---\n{memory}\n\n--- CRM ---\n{load_crm()}"
    return call_claude(system, f"Inbound message:\n\n{message}")

def run_sales_agent(message, triage, memory):
    system = f"{load_agent('sales_agent')}\n\n--- MEMORY ---\n{memory}\n\n--- CRM ---\n{load_crm()}\n\n--- TRIAGE ---\n{json.dumps(triage, indent=2)}"
    return call_claude(system, f"Original message:\n\n{message}")

def run_cs_agent(message, triage, memory):
    system = f"{load_agent('customer_service_agent')}\n\n--- MEMORY ---\n{memory}\n\n--- CRM ---\n{load_crm()}\n\n--- TRIAGE ---\n{json.dumps(triage, indent=2)}"
    return call_claude(system, f"Original message:\n\n{message}")

def run_briefing(message, triage, agent_result):
    system = load_agent('manager_briefing_agent')
    user = f"Original message: {message}\n\nTriage:\n{json.dumps(triage, indent=2)}\n\nAgent result:\n{json.dumps(agent_result, indent=2)}"
    return call_claude(system, user)


# ══════════════════════════════════════════════════════════════════════════
# TAG HELPERS
# ══════════════════════════════════════════════════════════════════════════

def tag(label, cls):
    return f'<span class="tag tag-{cls}">{label}</span>'

def render_tags(triage):
    html = ""
    cat = triage.get("category", "")
    urg = triage.get("urgency", "")
    sent = triage.get("sentiment", "")
    cat_cls = {"sales": "sales", "customer_service": "cs", "escalation": "escalation", "complex": "medium", "admin": "neutral"}.get(cat, "neutral")
    html += tag(cat, cat_cls)
    html += tag(urg, urg)
    html += tag(sent, sent)
    return html


# ══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def run_pipeline(message, status_container, result_container):
    memory = load_memory()
    results = {}

    with status_container:
        # ── Step 1 ────────────────────────────────────────────────────
        st.markdown('<div class="section-header">Pipeline Progress</div>', unsafe_allow_html=True)

        with st.spinner("Step 1 — Triage Agent classifying message..."):
            triage = run_triage(message, memory)
        results["triage"] = triage

        flags_html = "".join([f'<span class="flag-chip">{f}</span>' for f in triage.get("flags", [])])
        st.markdown(f"""
        <div class="bp-card">
            <div class="section-header">Step 1 — Triage Agent ✓</div>
            {render_tags(triage)}
            {f'<div style="margin-top:8px">{flags_html}</div>' if flags_html else ''}
            <div style="margin-top:10px;font-size:12px;color:#8b8f9e;font-family:'DM Mono',monospace;">
                Route → <span style="color:#e8ff6b">{triage.get('next_agent','').replace('_',' ').title()}</span>
            </div>
            <div style="margin-top:6px;font-size:12px;color:#8b8f9e;">{triage.get('triage_notes','')}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 2 ────────────────────────────────────────────────────
        next_agent = triage.get("next_agent", "customer_service_agent")
        category   = triage.get("category", "customer_service")
        agent_label = next_agent.replace("_", " ").title()

        with st.spinner(f"Step 2 — {agent_label} processing..."):
            if category in ("sales",) or next_agent == "sales_agent":
                agent_result = run_sales_agent(message, triage, memory)
            elif category == "admin":
                agent_result = {"summary": "Admin request — routed directly to briefing agent."}
            else:
                agent_result = run_cs_agent(message, triage, memory)
        results["agent"] = agent_result

        st.markdown(f"""
        <div class="bp-card-green">
            <div class="section-header">Step 2 — {agent_label} ✓</div>
            <div style="font-size:12px;color:#8b8f9e;font-family:'DM Mono',monospace;">
                Draft response prepared · Internal action logged
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 3 ────────────────────────────────────────────────────
        with st.spinner("Step 3 — Manager Briefing Agent summarising..."):
            briefing = run_briefing(message, triage, agent_result)
        results["briefing"] = briefing

        st.markdown(f"""
        <div class="bp-card-accent">
            <div class="section-header">Step 3 — Manager Briefing Agent ✓</div>
            <div style="font-size:12px;color:#8b8f9e;font-family:'DM Mono',monospace;">
                Telegram summary ready
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Save to DB ─────────────────────────────────────────────────
        log_event(message, triage, agent_result, briefing)
        open_task = agent_result.get("open_task") or (agent_result.get("crm_update") or {}).get("next_action")
        if open_task:
            add_task(open_task, triage.get("urgency", "medium"), "streamlit")
        if category == "sales" and "crm_update" in agent_result:
            cu = agent_result["crm_update"]
            contact = triage.get("customer_name") or triage.get("company_name") or "unknown"
            log_crm(contact, cu.get("status", "updated"), cu.get("notes", ""))

    # ── Render Results ─────────────────────────────────────────────────
    with result_container:
        st.markdown('<div class="section-header">Results</div>', unsafe_allow_html=True)

        # Telegram summary
        telegram = briefing.get("telegram_summary", "")
        st.markdown(f'<div class="telegram-box">{telegram}</div>', unsafe_allow_html=True)

        # Action / value / risk banners
        if briefing.get("needs_human_action"):
            st.markdown(f'<div class="action-banner">⚠️ <strong>Action needed:</strong> {briefing.get("human_action_required")}</div>', unsafe_allow_html=True)
        if briefing.get("value_flag"):
            st.markdown(f'<div class="value-banner">💰 <strong>Value opportunity:</strong> {briefing.get("value_flag")}</div>', unsafe_allow_html=True)
        if briefing.get("risk_flag"):
            st.markdown(f'<div class="risk-banner">🚨 <strong>Risk:</strong> {briefing.get("risk_flag")}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Draft response
        draft = agent_result.get("draft_response")
        if draft:
            st.markdown('<div class="section-header">Draft Response</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="draft-box">{draft}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Internal action
        internal = agent_result.get("internal_action") or (agent_result.get("crm_update") or {}).get("notes")
        if internal:
            st.markdown('<div class="section-header">Internal Action</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bp-card"><span style="font-size:13px;color:#8b8f9e">{internal}</span></div>', unsafe_allow_html=True)

    return results


# ══════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════

def main():
    init_db()

    # ── Sidebar ────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 20px">
            <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:#e8eaf0;letter-spacing:-0.5px">
                Bright<span style="color:#e8ff6b">Path</span>
            </div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1px;color:#555a6b;text-transform:uppercase;margin-top:2px">
                AI Operations
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">API Key</div>', unsafe_allow_html=True)
        api_input = st.text_input("", value=API_KEY, type="password", placeholder="sk-ant-...", label_visibility="collapsed")
        if api_input:
            globals()["API_KEY"] = api_input

        st.markdown("<br>", unsafe_allow_html=True)

        # Stats
        total, open_tasks, high, crm = get_counts()
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:20px">
            <div class="bp-card" style="text-align:center;padding:12px">
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#e8ff6b">{total}</div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b;text-transform:uppercase;letter-spacing:0.8px">Events</div>
            </div>
            <div class="bp-card" style="text-align:center;padding:12px">
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#ffa94d">{open_tasks}</div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b;text-transform:uppercase;letter-spacing:0.8px">Tasks</div>
            </div>
            <div class="bp-card" style="text-align:center;padding:12px">
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#ff6b6b">{high}</div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b;text-transform:uppercase;letter-spacing:0.8px">High Urgency</div>
            </div>
            <div class="bp-card" style="text-align:center;padding:12px">
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#6bffb8">{crm}</div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b;text-transform:uppercase;letter-spacing:0.8px">CRM Updates</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Model</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:#555a6b">{MODEL}</div>', unsafe_allow_html=True)

    # ── Main tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["RUN PIPELINE", "TASKS & HISTORY", "MEMORY FILES", "CRM DATA"])

    # ══════════════════════
    # TAB 1 — RUN PIPELINE
    # ══════════════════════
    with tab1:
        col_left, col_right = st.columns([1, 1], gap="large")

        with col_left:
            st.markdown('<div class="section-header">Inbound Message</div>', unsafe_allow_html=True)

            scenario = st.selectbox(
                "Load scenario",
                options=list(SCENARIOS.keys()),
                label_visibility="collapsed"
            )

            default_msg = SCENARIOS.get(scenario, "")
            message = st.text_area(
                "Message",
                value=default_msg,
                height=140,
                placeholder="Type or paste an inbound message...",
                label_visibility="collapsed"
            )

            run_clicked = st.button("▶  Run Pipeline", use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-header">Agent Pipeline</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="bp-card">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                    <div style="text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#e8ff6b;margin-bottom:4px">TRIAGE</div>
                        <div style="font-size:20px">🔀</div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b">Classify · Route</div>
                    </div>
                    <div style="color:#2a2d35;font-size:18px">→</div>
                    <div style="text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#6bffb8;margin-bottom:4px">SALES / CS</div>
                        <div style="font-size:20px">🧠</div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b">Act · Draft · Log</div>
                    </div>
                    <div style="color:#2a2d35;font-size:18px">→</div>
                    <div style="text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#ffa94d;margin-bottom:4px">BRIEFING</div>
                        <div style="font-size:20px">📋</div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b">Summarise · Alert</div>
                    </div>
                    <div style="color:#2a2d35;font-size:18px">→</div>
                    <div style="text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#74b9ff;margin-bottom:4px">TELEGRAM</div>
                        <div style="font-size:20px">✈️</div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#555a6b">Notify · Action</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            status_container = st.container()
            result_container = st.container()

            if run_clicked and message.strip():
                if not API_KEY:
                    st.error("Please enter your Anthropic API key in the sidebar.")
                else:
                    run_pipeline(message.strip(), status_container, result_container)
            elif run_clicked:
                st.warning("Please enter a message first.")

    # ══════════════════════
    # TAB 2 — TASKS & HISTORY
    # ══════════════════════
    with tab2:
        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown('<div class="section-header">Open Tasks</div>', unsafe_allow_html=True)
            tasks = get_tasks()
            if tasks:
                for t in tasks:
                    created, task, priority, status = t
                    p_colour = {"high": "#ff6b6b", "medium": "#ffa94d", "low": "#6bffb8"}.get(priority, "#8b8f9e")
                    st.markdown(f"""
                    <div class="bp-card" style="padding:12px 14px">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
                            <div style="font-size:13px;color:#c8cad4;flex:1">{task}</div>
                            <span class="tag" style="background:rgba(0,0,0,0.2);color:{p_colour};border:1px solid {p_colour};flex-shrink:0">{priority}</span>
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#555a6b;margin-top:6px">{created[:16]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="bp-card"><span style="color:#555a6b;font-size:13px">No tasks yet — run a scenario to generate tasks.</span></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-header">Event History</div>', unsafe_allow_html=True)
            events = get_events()
            if events:
                for e in events:
                    ts, cat, urg, sent, msg = e
                    cat_colour = {"sales": "#6bffb8", "customer_service": "#74b9ff", "escalation": "#ff6b9d", "admin": "#8b8f9e"}.get(cat, "#8b8f9e")
                    st.markdown(f"""
                    <div class="bp-card" style="padding:12px 14px">
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                            <span style="font-family:'DM Mono',monospace;font-size:10px;color:{cat_colour}">{(cat or '').upper()}</span>
                            <span style="font-family:'DM Mono',monospace;font-size:10px;color:#555a6b">{(ts or '')[:16]}</span>
                        </div>
                        <div style="font-size:12px;color:#8b8f9e">{(msg or '')[:80]}{'…' if len(msg or '')>80 else ''}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="bp-card"><span style="color:#555a6b;font-size:13px">No events yet.</span></div>', unsafe_allow_html=True)

    # ══════════════════════
    # TAB 3 — MEMORY FILES
    # ══════════════════════
    with tab3:
        st.markdown('<div class="section-header">Live Memory Files</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;color:#555a6b;margin-bottom:16px">These files are read by agents on every run. Edit them directly to update context.</div>', unsafe_allow_html=True)

        mem_files = {
            "customer_history.md": "👤 Customer History",
            "sales_notes.md": "💼 Sales Notes",
            "open_tasks.md": "✅ Open Tasks",
            "decision_log.md": "📋 Decision Log",
            "company_context.md": "🏢 Company Context",
        }

        cols = st.columns(2)
        for i, (fname, label) in enumerate(mem_files.items()):
            with cols[i % 2]:
                content = load_file(MEMORY / fname)
                st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:#e8ff6b;margin-bottom:6px">{label}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="memory-file">{content}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════
    # TAB 4 — CRM DATA
    # ══════════════════════
    with tab4:
        st.markdown('<div class="section-header">CRM Contacts</div>', unsafe_allow_html=True)
        crm_raw = load_crm()
        try:
            crm_data = json.loads(crm_raw)
            contacts = crm_data.get("contacts", [])
            cols = st.columns(2)
            for i, contact in enumerate(contacts):
                with cols[i % 2]:
                    is_vip = contact.get("vip", False)
                    card_class = "bp-card-accent" if is_vip else "bp-card"
                    name = contact.get("name", "Unknown")
                    company = contact.get("company", "")
                    status = contact.get("status", "")
                    tags_list = contact.get("tags", [])
                    tags_html = "".join([f'<span class="flag-chip">{t}</span>' for t in tags_list])
                    value = contact.get("annual_value") or contact.get("estimated_value") or contact.get("total_spend") or ""
                    value_str = f"£{value:,}" if isinstance(value, (int, float)) else ""

                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <div>
                                <div style="font-weight:600;font-size:14px;color:#e8eaf0">{name} {'⭐' if is_vip else ''}</div>
                                <div style="font-size:12px;color:#555a6b;font-family:'DM Mono',monospace">{company}</div>
                            </div>
                            {f'<div style="font-family:\'DM Mono\',monospace;font-size:13px;color:#6bffb8">{value_str}</div>' if value_str else ''}
                        </div>
                        <div style="margin-top:8px">
                            <span class="tag tag-neutral">{status.replace('_',' ')}</span>
                        </div>
                        <div style="margin-top:8px">{tags_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Could not load CRM: {e}")


if __name__ == "__main__":
    main()
