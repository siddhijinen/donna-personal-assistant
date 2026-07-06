import datetime
import json
import uuid
import re

# ==========================================
# 1. HARDCODED MOCK DATA STACKS
# ==========================================
MOCK_GMAIL_DATABASE = [
    {
        "id": "msg_001",
        "sender": "boss@company.com",
        "subject": "Urgent: Project Update",
        "body": "Please send the latest Q3 report by end of day.",
        "timestamp": "2026-07-06T09:00:00Z"
    },
    {
        "id": "msg_002",
        "sender": "marketing@veritas.com",
        "subject": "Veritas media team sync",
        "body": "Can we schedule a meeting tomorrow to discuss the new campaign?",
        "timestamp": "2026-07-06T10:15:00Z"
    },
    {
        "id": "msg_003",
        "sender": "noreply@github.com",
        "subject": "[GitHub] Security Alert",
        "body": "Dependabot found 2 vulnerabilities in your repository.",
        "timestamp": "2026-07-06T11:45:00Z"
    }
]

MOCK_CALENDAR_DATABASE = [
    {
        "id": "evt_001",
        "summary": "Team Standup",
        "start_time": "2026-07-07T10:00:00Z",
        "description": "Daily sync with the engineering team."
    },
    {
        "id": "evt_002",
        "summary": "Lunch with Client",
        "start_time": "2026-07-07T12:30:00Z",
        "description": "Discussing new contract terms."
    }
]

# ==========================================
# 2. LOCAL MCP SIMULATION FUNCTIONS
# ==========================================
def fetch_mock_emails(query: str = "") -> list:
    """Simulates fetching emails, optionally filtering by keyword."""
    print(f"[INFO] Local MCP: Executing 'fetch_mock_emails' with query: '{query}'...")
    if not query:
        print(f"[SUCCESS] Retrieved {len(MOCK_GMAIL_DATABASE)} emails.")
        return MOCK_GMAIL_DATABASE
    
    # Simple keyword match
    results = []
    query_lower = query.lower()
    for email in MOCK_GMAIL_DATABASE:
        if (query_lower in email["subject"].lower() or 
            query_lower in email["body"].lower() or 
            query_lower in email["sender"].lower()):
            results.append(email)
    
    print(f"[SUCCESS] Found {len(results)} matching email(s).")
    return results

def create_mock_calendar_event(summary: str, start_time: str, description: str = "") -> dict:
    """Simulates creating a calendar event and updating the local database."""
    print(f"[INFO] Local MCP: Executing 'create_mock_calendar_event'...")
    new_event = {
        "id": f"evt_{uuid.uuid4().hex[:6]}",
        "summary": summary,
        "start_time": start_time,
        "description": description
    }
    MOCK_CALENDAR_DATABASE.append(new_event)
    print(f"[SUCCESS] Event '{summary}' created successfully. (Total events: {len(MOCK_CALENDAR_DATABASE)})")
    return new_event

# ==========================================
# 3. AGENT PIPELINE & COMPILATION
# ==========================================
def simulate_gemini_routing(user_query: str) -> str:
    """Simulates an LLM intent routing layer (Orchestrator)."""
    query_lower = user_query.lower()
    if "schedule" in query_lower or "meeting" in query_lower or "calendar" in query_lower:
        return "calendar_tool"
    elif "email" in query_lower or "inbox" in query_lower or "message" in query_lower:
        return "gmail_tool"
    else:
        return "general_chat"

def simulate_gemini_extraction(user_query: str) -> dict:
    """Simulates LLM parameter extraction based on natural language."""
    # Fallback default values
    extracted = {
        "summary": "Meeting",
        "start_time": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat() + "Z",
        "description": "Automated meeting via agent"
    }
    
    # Hardcoded extraction logic matching the demo query
    if "veritas media team" in user_query.lower():
        extracted["summary"] = "Veritas Media Team Sync"
        extracted["description"] = "Discuss media campaign with Veritas"
        
        # Calculate tomorrow at 4 PM
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        extracted["start_time"] = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    return extracted

def run_agent_pipeline(user_query: str):
    """End-to-end execution pipeline."""
    print("-" * 60)
    print(f"[INFO] Agent Pipeline Initialized.")
    print(f"[USER QUERY] \"{user_query}\"")
    
    # Step 1: Routing
    print("[INFO] Routing query via Simulated LLM Orchestrator...")
    route = simulate_gemini_routing(user_query)
    print(f"[ROUTER] Intent identified: '{route}'")
    
    # Step 2: Execution
    agent_response = ""
    if route == "calendar_tool":
        print("[INFO] Delegating to Calendar Agent...")
        params = simulate_gemini_extraction(user_query)
        result = create_mock_calendar_event(
            summary=params["summary"], 
            start_time=params["start_time"], 
            description=params["description"]
        )
        agent_response = f"I have successfully scheduled the '{result['summary']}' for {result['start_time']}."
        
    elif route == "gmail_tool":
        print("[INFO] Delegating to Gmail Agent...")
        results = fetch_mock_emails()
        agent_response = f"You have {len(results)} emails in your inbox. Latest is from {results[-1]['sender']} about '{results[-1]['subject']}'."
        
    else:
        agent_response = "I am a helpful assistant. How can I assist you today?"
        
    # Step 3: Output Formatting
    print("\n" + "=" * 60)
    print("🤖 AGENT FINAL RESPONSE:")
    print("=" * 60)
    print(agent_response)
    print("=" * 60 + "\n")


# ==========================================
# 4. EXECUTION DEMONSTRATION
# ==========================================
if __name__ == "__main__":
    print("[INFO] Loading Mock Data Context...")
    print(f"[SUCCESS] Loaded {len(MOCK_GMAIL_DATABASE)} mock emails and {len(MOCK_CALENDAR_DATABASE)} mock events.\n")
    
    # Test Case 1: Calendar Scheduling (Complex Extraction)
    run_agent_pipeline("Schedule a meeting with the Veritas media team tomorrow at 4 PM")
    
    # Test Case 2: Email Fetching
    run_agent_pipeline("Check my email inbox for recent messages")
