"""
BrightPath Training — AI Operations Orchestrator
-------------------------------------------------
Run:  python orchestrator.py
Requires: pip install anthropic rich
Set:  ANTHROPIC_API_KEY environment variable
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import print as rprint

console = Console()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
AGENTS = BASE / "agents"
MEMORY = BASE / "memory"
DATA   = BASE / "data"
LOGS   = BASE / "logs"
DB     = BASE / "brightpath.db"

# ── Anthropic client ───────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"


# ══════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            message     TEXT,
            category    TEXT,
            urgency     TEXT,
            sentiment   TEXT,
            triage_out  TEXT,
            agent_out   TEXT,
            briefing    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created     TEXT,
            task        TEXT,
            priority    TEXT,
            status      TEXT DEFAULT 'open',
            source      TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS crm_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            contact     TEXT,
            action      TEXT,
            notes       TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_event(message, triage, agent_result, briefing):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (timestamp, message, category, urgency, sentiment, triage_out, agent_out, briefing)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        datetime.now().isoformat(),
        message,
        triage.get("category"),
        triage.get("urgency"),
        triage.get("sentiment"),
        json.dumps(triage),
        json.dumps(agent_result),
        json.dumps(briefing)
    ))
    conn.commit()
    conn.close()


def add_task(task_text, priority, source):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (created, task, priority, source)
        VALUES (?,?,?,?)
    """, (datetime.now().isoformat(), task_text, priority, source))
    conn.commit()
    conn.close()


def log_crm(contact, action, notes):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO crm_log (timestamp, contact, action, notes)
        VALUES (?,?,?,?)
    """, (datetime.now().isoformat(), contact, action, notes))
    conn.commit()
    conn.close()


def show_tasks():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT created, task, priority, status FROM tasks ORDER BY created DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()

    table = Table(title="Open Tasks", show_header=True, header_style="bold yellow")
    table.add_column("Created", style="dim", width=20)
    table.add_column("Task")
    table.add_column("Priority", width=10)
    table.add_column("Status", width=10)
    for row in rows:
        colour = {"high": "red", "medium": "yellow", "low": "green"}.get(row[2], "white")
        table.add_row(row[0][:16], row[1], f"[{colour}]{row[2]}[/{colour}]", row[3])
    console.print(table)


def show_history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT timestamp, category, urgency, sentiment, message FROM events ORDER BY timestamp DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()

    table = Table(title="Recent Events", show_header=True, header_style="bold cyan")
    table.add_column("Time", width=18)
    table.add_column("Category", width=14)
    table.add_column("Urgency", width=10)
    table.add_column("Sentiment", width=10)
    table.add_column("Message")
    for row in rows:
        table.add_row(row[0][:16], row[1] or "-", row[2] or "-", row[3] or "-", (row[4] or "")[:60] + "…")
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
# FILE LOADERS
# ══════════════════════════════════════════════════════════════════════════

def load_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def load_agent(name: str) -> str:
    return load_file(AGENTS / f"{name}.md")

def load_memory() -> str:
    files = ["company_context.md", "customer_history.md", "sales_notes.md", "open_tasks.md"]
    combined = []
    for f in files:
        content = load_file(MEMORY / f)
        if content:
            combined.append(f"## {f}\n\n{content}")
    return "\n\n---\n\n".join(combined)

def load_crm() -> str:
    path = DATA / "crm.json"
    if path.exists():
        data = json.loads(path.read_text())
        return json.dumps(data, indent=2)
    return "{}"


# ══════════════════════════════════════════════════════════════════════════
# CLAUDE CALLS
# ══════════════════════════════════════════════════════════════════════════

def call_claude(system_prompt: str, user_message: str, label: str) -> dict:
    console.print(f"  [dim]→ calling {label}...[/dim]")
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        console.print(f"  [red]JSON parse error in {label}: {e}[/red]")
        return {"error": str(e), "raw": raw}
    except Exception as e:
        console.print(f"  [red]API error in {label}: {e}[/red]")
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════════════════

def run_triage(message: str, memory: str) -> dict:
    system = f"""
{load_agent('triage_agent')}

--- MEMORY CONTEXT ---
{memory}

--- CRM ---
{load_crm()}
"""
    return call_claude(system, f"Inbound message:\n\n{message}", "Triage Agent")


def run_sales_agent(message: str, triage: dict, memory: str) -> dict:
    system = f"""
{load_agent('sales_agent')}

--- MEMORY CONTEXT ---
{memory}

--- CRM ---
{load_crm()}

--- TRIAGE NOTES ---
{json.dumps(triage, indent=2)}
"""
    return call_claude(system, f"Original message:\n\n{message}", "Sales Agent")


def run_customer_service_agent(message: str, triage: dict, memory: str) -> dict:
    system = f"""
{load_agent('customer_service_agent')}

--- MEMORY CONTEXT ---
{memory}

--- CRM ---
{load_crm()}

--- TRIAGE NOTES ---
{json.dumps(triage, indent=2)}
"""
    return call_claude(system, f"Original message:\n\n{message}", "Customer Service Agent")


def run_manager_briefing(message: str, triage: dict, agent_result: dict) -> dict:
    system = load_agent('manager_briefing_agent')
    user = f"""
Original message: {message}

Triage result:
{json.dumps(triage, indent=2)}

Specialist agent result:
{json.dumps(agent_result, indent=2)}
"""
    return call_claude(system, user, "Manager Briefing Agent")


# ══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════

def process_message(message: str):
    console.rule("[bold yellow]BrightPath Orchestrator[/bold yellow]")
    console.print(Panel(message, title="[bold]Inbound Message[/bold]", border_style="dim"))

    memory = load_memory()

    # ── Step 1: Triage ─────────────────────────────────────────────────
    console.print("\n[bold cyan]Step 1 — Triage Agent[/bold cyan]")
    triage = run_triage(message, memory)
    if "error" in triage:
        console.print(f"[red]Triage failed: {triage}[/red]")
        return

    console.print(f"  Category : [yellow]{triage.get('category')}[/yellow]")
    console.print(f"  Urgency  : [yellow]{triage.get('urgency')}[/yellow]")
    console.print(f"  Sentiment: [yellow]{triage.get('sentiment')}[/yellow]")
    console.print(f"  Route to : [yellow]{triage.get('next_agent')}[/yellow]")
    if triage.get("flags"):
        console.print(f"  Flags    : [red]{', '.join(triage['flags'])}[/red]")

    # ── Step 2: Specialist Agent ────────────────────────────────────────
    next_agent = triage.get("next_agent", "customer_service_agent")
    category   = triage.get("category", "customer_service")

    console.print(f"\n[bold cyan]Step 2 — {next_agent.replace('_', ' ').title()}[/bold cyan]")

    if category in ("sales", "complex") and next_agent == "sales_agent":
        agent_result = run_sales_agent(message, triage, memory)
    elif category in ("admin",):
        agent_result = {"summary": "Admin/manager request — handled by briefing agent directly"}
    else:
        agent_result = run_customer_service_agent(message, triage, memory)

    if "error" in agent_result:
        console.print(f"[red]Agent error: {agent_result}[/red]")
        return

    # Show draft response if present
    draft = agent_result.get("draft_response")
    if draft:
        console.print(Panel(draft, title="[bold]Draft Response[/bold]", border_style="green"))

    # ── Step 3: Manager Briefing ────────────────────────────────────────
    console.print("\n[bold cyan]Step 3 — Manager Briefing Agent[/bold cyan]")
    briefing = run_manager_briefing(message, triage, agent_result)

    # ── Save to DB ──────────────────────────────────────────────────────
    log_event(message, triage, agent_result, briefing)

    # Add task if needed
    open_task = agent_result.get("open_task") or agent_result.get("crm_update", {}).get("next_action")
    if open_task:
        add_task(open_task, triage.get("urgency", "medium"), "orchestrator")

    # Log CRM update if sales
    if category == "sales" and "crm_update" in agent_result:
        cu = agent_result["crm_update"]
        contact = triage.get("customer_name") or triage.get("company_name") or "unknown"
        log_crm(contact, cu.get("status", "updated"), cu.get("notes", ""))

    # ── Telegram Summary ────────────────────────────────────────────────
    console.rule("[bold yellow]📱 Telegram Summary[/bold yellow]")
    console.print(Panel(
        briefing.get("telegram_summary", "No summary generated."),
        border_style="yellow"
    ))

    if briefing.get("needs_human_action"):
        console.print(f"\n[bold red]⚠  ACTION NEEDED:[/bold red] {briefing.get('human_action_required')}")

    if briefing.get("value_flag"):
        console.print(f"[bold green]💰 VALUE:[/bold green] {briefing.get('value_flag')}")

    if briefing.get("risk_flag"):
        console.print(f"[bold red]🚨 RISK:[/bold red] {briefing.get('risk_flag')}")

    console.rule()


# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════

SCENARIOS = {
    "1":  ("Sales lead", "Hi, we're looking for leadership training for 30 managers in May. Can you send pricing? We're comparing a few providers. — Marcus, Operations Director, Pinnacle Group"),
    "2":  ("Customer booking change", "Hi, I need to move my workshop booking from April to June. I'm booked onto the 8th April Presentation Skills session. Thanks, James Cooper"),
    "3":  ("Angry customer complaint", "This is absolutely unacceptable. I attended your Managing People workshop last month and the trainer was unprepared and the materials were out of date. I want a full refund and an explanation. — Linda Okafor"),
    "4":  ("VIP upsell", "Hi, it's Dan from Nexus Digital. We're really happy with the partnership so far. Any chance we could add some 1:1 coaching for three of our senior managers this quarter?"),
    "5":  ("Duplicate/returning lead", "Hello, I'm reaching out from Acme Logistics. We're interested in corporate training for our management team — about 25 people. Can you send information? — Sarah Miles, HR Director"),
    "6":  ("Multi-request email", "Hi, I need to change my booking for next week AND can you resend my invoice as I can't find it AND also — are you planning any resilience workshops this year? Thanks, Tom Nguyen"),
    "7":  ("Cold lead re-engagement", "Hi there, Rachel Drummond from Stormfront Media. We spoke a couple of months ago about leadership training. We've finally got budget confirmed. Are you still running programmes?"),
    "8":  ("Competitor mention", "We've been comparing training providers and Leadership Lab is offering the same course for 20% less. Can you match that price for our team of 15?"),
    "9":  ("Refund — policy edge case", "Hi, I booked the April workshop last month but unfortunately I've just been made redundant and can no longer afford it. I know it might be outside your cancellation window but is there any flexibility? — Greg Walsh"),
    "10": ("Manager daily briefing", "Show me a summary of everything open and urgent today. What needs my attention?"),
}

def print_menu():
    console.print("\n[bold]BrightPath AI Operations System[/bold]")
    console.print("[dim]Choose a scenario or type your own message\n[/dim]")
    table = Table(show_header=False, box=None, padding=(0,1))
    table.add_column(style="bold yellow", width=4)
    table.add_column(style="white")
    for k, (name, _) in SCENARIOS.items():
        table.add_row(f"[{k}]", name)
    table.add_row("[t]", "[dim]Show open tasks[/dim]")
    table.add_row("[h]", "[dim]Show event history[/dim]")
    table.add_row("[q]", "[dim]Quit[/dim]")
    console.print(table)


def main():
    init_db()
    console.print("[bold green]✓ BrightPath Orchestrator ready[/bold green]")
    console.print(f"[dim]Model: {MODEL} | DB: {DB}[/dim]")

    while True:
        print_menu()
        choice = console.input("\n[bold]> [/bold]").strip()

        if choice.lower() == "q":
            console.print("[dim]Goodbye.[/dim]")
            break
        elif choice.lower() == "t":
            show_tasks()
        elif choice.lower() == "h":
            show_history()
        elif choice in SCENARIOS:
            name, message = SCENARIOS[choice]
            console.print(f"\n[dim]Running scenario: {name}[/dim]")
            process_message(message)
        elif choice.strip():
            process_message(choice)
        else:
            console.print("[dim]No input.[/dim]")

def process_message_for_telegram(message: str) -> dict:
    """Silent version of process_message() — returns result dict for Telegram."""
    memory = load_memory()

    triage = run_triage(message, memory)
    if "error" in triage:
        return {"summary": f"❌ Triage error: {triage.get('error')}", "action": None}

    category  = triage.get("category", "customer_service")
    next_agent = triage.get("next_agent", "customer_service_agent")

    if category in ("sales", "complex") and next_agent == "sales_agent":
        agent_result = run_sales_agent(message, triage, memory)
    elif category == "admin":
        agent_result = {"summary": "Admin request — handled by briefing agent."}
    else:
        agent_result = run_customer_service_agent(message, triage, memory)

    if "error" in agent_result:
        return {"summary": f"❌ Agent error: {agent_result.get('error')}", "action": None}

    briefing = run_manager_briefing(message, triage, agent_result)
    log_event(message, triage, agent_result, briefing)

    open_task = agent_result.get("open_task") or agent_result.get("crm_update", {}).get("next_action")
    if open_task:
        add_task(open_task, triage.get("urgency", "medium"), "telegram")

    if category == "sales" and "crm_update" in agent_result:
        cu = agent_result["crm_update"]
        contact = triage.get("customer_name") or triage.get("company_name") or "unknown"
        log_crm(contact, cu.get("status", "updated"), cu.get("notes", ""))

    return {
        "summary": briefing.get("telegram_summary", "No summary."),
        "action":  briefing.get("human_action_required") if briefing.get("needs_human_action") else None,
        "value":   briefing.get("value_flag"),
        "risk":    briefing.get("risk_flag"),
    }

if __name__ == "__main__":
    main()
