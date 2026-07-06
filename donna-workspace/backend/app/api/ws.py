from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from backend.app.orchestrator import donna_orchestrator
from backend.app.guardrails import security_rail_middleware, SecurityException
from backend.app.notifications import notification_clients
import json

router = APIRouter()

active_sessions = {
    "current_state_pool": {
        "status": "WAIT_FOR_APPROVAL",
        "requires_approval": True
    }
}

@router.websocket("/ws/notifications")
async def notifications_endpoint(websocket: WebSocket):
    await websocket.accept()
    notification_clients.add(websocket)
    try:
        while True:
            # Just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_clients.remove(websocket)
        print("[WS] Notification client disconnected.")

@router.websocket("/ws/handshake")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            user_text = payload.get("text", "")

            # Guardrail validation
            try:
                await security_rail_middleware(user_text)
            except SecurityException as e:
                await websocket.send_json({
                    "status": "SUCCESS",
                    "agent_response": f"ALERT: Security Guardrail Exception Triggered. Reason: {e.message}",
                    "logs": [f"🛑 Guardrail blocked: {e.message}"]
                })
                continue

            initial_state = {
                "user_input": user_text,
                "sanitized_input": user_text,
                "execution_logs": ["WebSocket handshake established safely.", "Guardrail checks passed."],
                "requires_approval": False
            }

            try:
                final_state = await donna_orchestrator.ainvoke(initial_state)

                await websocket.send_json({
                    "status": "WAIT_FOR_APPROVAL" if final_state.get("requires_approval") else "SUCCESS",
                    "agent_response": final_state.get("agent_response") or "Payload updated successfully.",
                    "logs": final_state.get("execution_logs", ["Agent routine completed."]),
                    "drafted_reply": final_state.get("drafted_reply"),
                    "requires_approval": final_state.get("requires_approval", False),
                    "sensitivity_reason": final_state.get("sensitivity_reason", "")
                })
            except Exception as core_err:
                await websocket.send_json({
                    "status": "SUCCESS",
                    "agent_response": f"Core Orchestrator Error: {str(core_err)}",
                    "logs": [f"🐛 Internal Graph Error: {str(core_err)}"]
                })

    except WebSocketDisconnect:
        print("[WS] Front-end streaming node dropped connection safely.")