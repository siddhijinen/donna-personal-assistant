import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from backend.app.llm import ask_gemini
from backend.app.payments import create_payment_link
from backend.app.mcp_clients import call_google_workspace_tool
from backend.app.database import AsyncSessionLocal
from backend.app.models import ExpenseRecord
import re

class AgentState(TypedDict):
    user_input: str
    sanitized_input: str
    route_target: str
    agent_response: str
    execution_logs: list[str]
    requires_approval: bool
    drafted_reply: str
    sensitivity_reason: str


# --- Routing ---
async def supervisor_router_node(state: AgentState) -> dict:
    text = state["sanitized_input"]
    logs = state.get("execution_logs", []) or []
    logs.append("Orchestrator checking intent via Gemini...")

    prompt = f"""
    Classify this user request into exactly one category:
    - communications (email via Gmail)
    - calendar (scheduling via Google Calendar)
    - logistics (web search, flights, hotels, general lookup)
    - ledger (expenses, payments, Razorpay)
    - general (greetings, help, chitchat)
    
    User request: "{text}"
    
    Respond with ONLY the category name in lowercase.
    """
    target = await ask_gemini(prompt)
    target = target.strip().lower()
    
    # Map to node names
    if "communication" in target:
        route = "communications_agent"
    elif "calendar" in target:
        route = "calendar_agent"
    elif "logistic" in target:
        route = "logistics_agent"
    elif "ledger" in target:
        route = "ledger_agent"
    else:
        route = "general_agent"

    return {"route_target": route, "execution_logs": logs + [f"Routing allocated to -> {route}"]}


# --- Communications (Gmail) ---
async def communications_agent_node(state: AgentState) -> dict:
    logs = state["execution_logs"] + ["Communications agent checking Gmail MCP..."]
    text = state["sanitized_input"]
    
    requires_approval = False
    reason = ""
    
    if "send" in text.lower() or "email" in text.lower() and ("to" in text.lower() or "saying" in text.lower()):
        # Sending email
        requires_approval = True
        reason = "Sending an email"
        # We don't actually send yet if it requires approval (it's handled via verify-action later)
        # But for the plan, we'll draft it.
        logs.append("Drafting email...")
        response = await ask_gemini(f"Draft an email based on this request: {text}. Output only the body.")
        return {
            "agent_response": f"I've prepared the email. Please authorize to send.",
            "drafted_reply": response,
            "requires_approval": True,
            "sensitivity_reason": reason,
            "execution_logs": logs + ["Awaiting authorization to send email."]
        }
    else:
        # Reading email
        logs.append("Searching emails...")
        mcp_res = await call_google_workspace_tool("search_emails", {"query": "in:inbox", "maxResults": 5})
        summary = await ask_gemini(f"Summarize these emails for the user based on their request '{text}':\n{mcp_res}")
        return {
            "agent_response": summary,
            "requires_approval": False,
            "execution_logs": logs + ["Email search complete."]
        }


# --- Calendar ---
async def calendar_agent_node(state: AgentState) -> dict:
    logs = state["execution_logs"] + ["Calendar agent checking Google Calendar MCP..."]
    text = state["sanitized_input"]
    
    if "delete" in text.lower() or "cancel" in text.lower():
        requires_approval = True
        reason = "Deleting a calendar event"
        return {
            "agent_response": "Please authorize to delete the calendar event.",
            "requires_approval": True,
            "sensitivity_reason": reason,
            "execution_logs": logs + ["Awaiting authorization to delete event."]
        }
    elif "schedule" in text.lower() or "book" in text.lower() or "create" in text.lower() or "add" in text.lower():
        logs.append("Extracting event details...")
        # Use Gemini to extract structured event fields
        now_iso = __import__('datetime').datetime.now().isoformat()
        extract_prompt = f"""
        Extract calendar event details from this user request and return ONLY a valid JSON object (no markdown).
        Today's datetime: {now_iso}
        Keys to include:
        - "summary": event title (string)
        - "start": {{"dateTime": "<ISO 8601 datetime e.g. 2026-07-07T10:00:00+05:30>"}}
        - "end": {{"dateTime": "<ISO 8601 datetime, typically 1 hour after start>"}}
        User request: "{text}"
        """
        raw_event_json = await ask_gemini(extract_prompt)
        cleaned = raw_event_json.replace("```json", "").replace("```", "").strip()
        import json as _json
        try:
            event_body = _json.loads(cleaned)
        except Exception:
            event_body = {"summary": text, "start": {"dateTime": now_iso + "+05:30"}, "end": {"dateTime": now_iso + "+05:30"}}
        mcp_res = await call_google_workspace_tool("create_event", {"calendarId": "primary", **event_body})
        summary = await ask_gemini(f"Confirm this calendar event creation result to the user in one sentence:\n{mcp_res}")
        return {
             "agent_response": summary,
             "requires_approval": False,
             "execution_logs": logs + ["Event creation attempted."]
        }
    else:
        logs.append("Listing events...")
        mcp_res = await call_google_workspace_tool("list_events", {"calendarId": "primary", "maxResults": 10})
        summary = await ask_gemini(f"Summarize these calendar events based on user request '{text}':\n{mcp_res}")
        return {
             "agent_response": summary,
             "requires_approval": False,
             "execution_logs": logs + ["Calendar query complete."]
        }


# --- Logistics (Web Search / General) ---
async def logistics_agent_node(state: AgentState) -> dict:
    logs = state["execution_logs"] + ["Logistics agent analyzing request..."]
    text = state["sanitized_input"]
    
    # In a real app, this might call SerpAPI. For now, we use Gemini's inherent knowledge.
    response = await ask_gemini(f"Answer this logistics/travel/general query concisely: {text}")
    
    return {
        "agent_response": response,
        "requires_approval": False,
        "execution_logs": logs + ["Logistics query complete."]
    }


# --- Ledger (Expenses & Razorpay) ---
async def ledger_agent_node(state: AgentState) -> dict:
    logs = state["execution_logs"] + ["Ledger & Expense Agent activated."]
    text = state["sanitized_input"]
    
    # Razorpay payment operations
    if "pay" in text.lower() or "charge" in text.lower() or "razorpay" in text.lower() or "invoice" in text.lower():
        logs.append("Razorpay operation detected.")
        amounts = re.findall(r"(?:₹|\$|rs\.?)?\s*(\d+(?:\.\d{2})?)", text, re.IGNORECASE)
        amount = float(amounts[0]) if amounts else 0.0
        
        if amount > 0:
            link_msg = create_payment_link(amount, f"Payment for: {text}")
            return {
                "agent_response": f"I have generated a Razorpay payment link for ₹{amount:.2f}: \n{link_msg}",
                "requires_approval": False,
                "execution_logs": logs + ["Generated Razorpay payment link."]
            }
        else:
            return {
                "agent_response": "Please specify the amount you want to create a Razorpay payment link for.",
                "requires_approval": False,
                "execution_logs": logs + ["Amount not detected for payment."]
            }
            
    # Expense tracking (Local DB)
    if "expense" in text.lower() or "spent" in text.lower() or "cost" in text.lower():
        amounts = re.findall(r"\$(\d+(?:\.\d{2})?)", text)
        amount = float(amounts[0]) if amounts else 0.0
        
        if amount > 200:
             return {
                "agent_response": f"Please authorize large expense entry of ${amount:.2f}.",
                "requires_approval": True,
                "sensitivity_reason": f"Expense of ${amount:.2f} exceeds $200 threshold",
                "execution_logs": logs + ["Awaiting authorization for large expense."]
            }
        elif amount > 0:
             logs.append("Recording expense...")
             cat = await ask_gemini(f"What is the category for this expense? '{text}'. Return ONLY the category name.")
             async with AsyncSessionLocal() as session:
                 new_expense = ExpenseRecord(amount=amount, category=cat.strip(), description=text)
                 session.add(new_expense)
                 await session.commit()
             return {
                 "agent_response": f"Recorded expense of ${amount:.2f} under {cat.strip()}.",
                 "requires_approval": False,
                 "execution_logs": logs + ["Expense recorded in DB."]
             }
        else:
            # Query expenses
            logs.append("Querying expenses...")
            # Simple mock for query since we'd need complex SQLAlchemy here for a real natural language query
            return {
                "agent_response": "I can query your expenses if you ask about specific amounts or categories.",
                "requires_approval": False,
                "execution_logs": logs + ["Expense query complete."]
            }

    return {
        "agent_response": "I couldn't identify a specific financial action.",
        "requires_approval": False,
        "execution_logs": logs
    }
    
# --- General ---
async def general_agent_node(state: AgentState) -> dict:
    logs = state["execution_logs"] + ["General agent activated."]
    response = await ask_gemini(state["sanitized_input"], system="You are Donna, a helpful, professional AI assistant.")
    return {
        "agent_response": response,
        "requires_approval": False,
        "execution_logs": logs + ["General response generated."]
    }

# --- LangGraph Structural Assembly ---
workflow = StateGraph(AgentState)

# Append functional graph node steps
workflow.add_node("supervisor", supervisor_router_node)
workflow.add_node("communications_agent", communications_agent_node)
workflow.add_node("calendar_agent", calendar_agent_node)
workflow.add_node("logistics_agent", logistics_agent_node)
workflow.add_node("ledger_agent", ledger_agent_node)
workflow.add_node("general_agent", general_agent_node)

# Map edge connections and conditional matrices
workflow.set_entry_point("supervisor")
workflow.add_conditional_edges("supervisor", lambda state: state["route_target"], {
    "communications_agent": "communications_agent",
    "calendar_agent": "calendar_agent",
    "logistics_agent": "logistics_agent",
    "ledger_agent": "ledger_agent",
    "general_agent": "general_agent"
})

workflow.add_edge("communications_agent", END)
workflow.add_edge("calendar_agent", END)
workflow.add_edge("logistics_agent", END)
workflow.add_edge("ledger_agent", END)
workflow.add_edge("general_agent", END)

# Compile ready runtime orchestrator
donna_orchestrator = workflow.compile()