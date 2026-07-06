"""
Background notification poller for proactive Gmail and Calendar alerts.
Runs every 60 seconds, pushes notifications to connected WebSocket clients.
"""
import asyncio
import json
from datetime import datetime, timedelta
from backend.app.mcp_clients import call_google_workspace_tool


from backend.app.llm import ask_gemini

# Connected WebSocket clients for broadcasting
notification_clients: set = set()


async def check_new_emails() -> list[dict]:
    """Check for unread emails received in the last 2 minutes."""
    notifications = []
    try:
        result = await call_google_workspace_tool(
            "search_emails",
            {"query": "is:unread newer_than:2m", "maxResults": 5}
        )
        if result and "error" not in result.lower() and "no results" not in result.lower():
            # Summarize Gmail output into a clean user notification
            prompt = f"Summarize this raw email search output into a single short sentence for a notification toast (e.g., 'New email from John: Meeting tomorrow'). Keep it short and clean. Raw:\n{result}"
            summary = await ask_gemini(prompt)
            if "error" not in summary.lower():
                notifications.append({
                    "type": "email",
                    "title": "New Email",
                    "message": summary,
                    "timestamp": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[Notification] Gmail check failed: {e}")
    return notifications


async def check_calendar_conflicts() -> list[dict]:
    """Check for upcoming events and detect overlaps."""
    notifications = []
    try:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        result = await call_google_workspace_tool(
            "list_events",
            {
                "calendarId": "primary",
                "timeMin": now.isoformat() + "Z",
                "timeMax": tomorrow.isoformat() + "Z",
                "maxResults": 20,
            }
        )
        if result and "error" not in result.lower() and "no results" not in result.lower():
            # Summarize Calendar output and look for conflicts or events starting within 15 minutes
            prompt = f"Look at this list of calendar events. Summarize any upcoming conflicts or events starting within 15 minutes. If there are none, return 'No upcoming conflicts'. Keep the summary to one short sentence for a notification toast. Raw:\n{result}"
            summary = await ask_gemini(prompt)
            if "error" not in summary.lower() and "no upcoming conflicts" not in summary.lower():
                notifications.append({
                    "type": "calendar",
                    "title": "Calendar Alert",
                    "message": summary,
                    "timestamp": now.isoformat(),
                })
    except Exception as e:
        print(f"[Notification] Calendar check failed: {e}")
    return notifications


async def broadcast_notification(notification: dict):
    """Send a notification to all connected WebSocket clients."""
    dead_clients = set()
    message = json.dumps(notification)
    for ws in notification_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead_clients.add(ws)
    notification_clients.difference_update(dead_clients)


async def notification_poller():
    """Main polling loop — runs every 60 seconds."""
    # Wait a bit on startup to let everything initialize
    await asyncio.sleep(10)
    print("[Notification] Background poller started.")

    while True:
        try:
            # Check Gmail
            email_notifications = await check_new_emails()
            for notif in email_notifications:
                await broadcast_notification(notif)

            # Check Calendar
            calendar_notifications = await check_calendar_conflicts()
            for notif in calendar_notifications:
                await broadcast_notification(notif)

        except Exception as e:
            print(f"[Notification] Poller cycle error: {e}")

        await asyncio.sleep(60)
