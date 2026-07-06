import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
from dotenv import load_dotenv

from backend.app.api.ws import router as websocket_router
from backend.app.database import init_db, AsyncSessionLocal
from backend.app.models import UserPasscode
from backend.app.notifications import notification_poller
from sqlalchemy import select

from pathlib import Path

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import shutil

def setup_google_mcp_credentials():
    """Ensure credentials.json is copied to home directory as required by @alanxchen/google-workspace-mcp."""
    backend_dir = Path(__file__).resolve().parent.parent
    src_path = backend_dir / "credentials.json"
    
    if src_path.exists():
        home = Path.home()
        dest_dir = home / ".google-workspace-mcp"
        dest_path = dest_dir / "credentials.json"
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        if not dest_path.exists() or src_path.stat().st_mtime > dest_path.stat().st_mtime:
            shutil.copy2(src_path, dest_path)
            print(f"[Credentials] Synced credentials.json to {dest_path}")
    else:
        print("[Credentials] Warning: No credentials.json found in backend folder.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_google_mcp_credentials()
    await init_db()
    asyncio.create_task(notification_poller())
    yield
    # Shutdown
    pass

app = FastAPI(title="Donna Agentic Engine Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth Endpoints ---

class SetupPayload(BaseModel):
    passcode: str

class LoginPayload(BaseModel):
    passcode: str

@app.get("/api/v1/auth/status")
async def auth_status():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserPasscode).limit(1))
        has_passcode = result.scalar_one_or_none() is not None
    return {"has_passcode": has_passcode}

@app.post("/api/v1/auth/setup")
async def setup_auth(payload: SetupPayload):
    if len(payload.passcode) < 6:
        raise HTTPException(status_code=400, detail="Passcode must be at least 6 characters.")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserPasscode).limit(1))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="Passcode already set.")
            
        hashed = bcrypt.hashpw(payload.passcode.encode('utf-8'), bcrypt.gensalt())
        new_passcode = UserPasscode(passcode_hash=hashed.decode('utf-8'))
        session.add(new_passcode)
        await session.commit()
        
    return {"status": "SUCCESS"}

@app.post("/api/v1/auth/login")
async def login(payload: LoginPayload):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserPasscode).limit(1))
        record = result.scalar_one_or_none()
        
        if record is None:
            raise HTTPException(status_code=400, detail="No passcode set up.")
            
        if not bcrypt.checkpw(payload.passcode.encode('utf-8'), record.passcode_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid passcode.")
            
    return {"status": "SUCCESS", "token": "session_active"}

@app.post("/api/v1/verify-action")
async def verify_action(payload: LoginPayload):
    # In a real app we'd execute the pending action here after verification
    # For Donna, the frontend sends this just to verify before telling the user it succeeded.
    # We use the same logic as login.
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserPasscode).limit(1))
        record = result.scalar_one_or_none()
        
        if record is None:
            raise HTTPException(status_code=400, detail="No passcode set up.")
            
        if not bcrypt.checkpw(payload.passcode.encode('utf-8'), record.passcode_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid passcode.")
            
    return {"status": "SUCCESS", "detail": "Action authorized."}

@app.get("/api/v1/calendar/agenda")
async def get_agenda():
    from backend.app.mcp_clients import call_google_workspace_tool
    from backend.app.llm import ask_gemini
    from datetime import datetime, timezone, timedelta
    import json
    try:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        raw_events = await call_google_workspace_tool(
            "list_events", 
            {
                "calendarId": "primary",
                "maxResults": 20,
                "timeMin": start_of_day.isoformat(),
                "timeMax": end_of_day.isoformat(),
            }
        )
        if not raw_events or "error" in raw_events.lower() or "no results" in raw_events.lower():
            return []
            
        prompt = f"""
        Extract the event list from this raw Google Calendar response. 
        Format it as a valid JSON array of objects, where each object has keys:
        - "title" (string, name of event)
        - "time" (string, local time range e.g. "10:00 AM - 11:00 AM" or "All day")
        
        If there are no events, return an empty array [].
        Do not return any markdown wrappers, just the raw JSON array.
        
        Raw response:
        {raw_events}
        """
        gemini_response = await ask_gemini(prompt)
        cleaned_json = gemini_response.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"[Calendar Endpoint] Error fetching agenda: {e}")
        return []

# Attach WebSocket routes
app.include_router(websocket_router)