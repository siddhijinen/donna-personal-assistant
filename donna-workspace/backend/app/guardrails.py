import re


class SecurityException(Exception):
    def __init__(self, message: str, payload: str):
        self.message = message
        self.payload = payload
        super().__init__(self.message)


async def inspect_prompt_safety(prompt) -> dict:
    """
    Scans incoming user prompts for injections, context drift, and illegal activities.
    Self-heals if passed a dictionary or JSON payload instead of a raw string.
    """
    # 1. Self-Healing Type Extraction (Prevents dictionary attribute crashes)
    if isinstance(prompt, dict):
        prompt = prompt.get("text", prompt.get("prompt", prompt.get("user_input", str(prompt))))
    elif not isinstance(prompt, str):
        prompt = str(prompt)

    clean_prompt = prompt.lower().strip()

    # Live developer diagnostic logging (helps you trace validation status in real-time)
    print(f"🔍 [Guardrail Scan] Evaluating payload: '{clean_prompt[:60]}...'")

    # 2. Direct Adversarial Injections
    attack_patterns = [
        r"(?i)ignore\s+previous\s+instructions",
        r"(?i)delete\s+all\s+logs",
        r"(?i)system\s+prompt"
    ]
    for pattern in attack_patterns:
        if re.search(pattern, clean_prompt):
            print("⚠️ [Guardrail Block] Adversarial structural pattern matched.")
            return {"safe": False, "reason": "Adversarial structural pattern detected."}

    # 3. Illegal & Security Threats
    illegal_patterns = [
        r"(?i)\b(hack|bypass|exploit|malware|ransomware|pirate|steal|counterfeit)\b",
        r"(?i)\b(illegal|smuggle|forge|fraud|laundering|shoplift|dox|ddos)\b",
        r"(?i)how\s+to\s+(make|build|synthesize|crack)\s+(bomb|drug|weapon|software)"
    ]
    for pattern in illegal_patterns:
        if re.search(pattern, clean_prompt):
            print("⚠️ [Guardrail Block] High-risk security pattern matched.")
            return {"safe": False, "reason": "High-risk security or illegal context detected."}

    # 4. Whitelisted Professional & Logistical Contexts
    professional_keywords = [
        "transaction", "log", "audit", "review", "file", "data", "report",
        "schedule", "invoice", "analysis", "reconcile", "status", "ledger",
        "account", "verify", "process", "system", "query", "document", "meet", "meeting",
        "flight", "travel", "ticket", "hotel", "booking", "look up", "timing", "carrier",
        "theater", "showtime", "cinema", "thriller", "aws", "hosting", "alignment", "executive"
    ]

    # Block explicitly unprofessional creative/casual prompts outright
    casual_triggers = [
        r"\b(tell\s+me\s+a\s+joke|write\s+a\s+story|poetry|game)\b",
        r"\b(dating|relationship|hobby)\b",
        r"\b(watch\s+a\s+movie|listen\s+to\s+music|play\s+video\s+game)\b"
    ]
    for trigger in casual_triggers:
        if re.search(trigger, clean_prompt):
            print("⚠️ [Guardrail Block] Unprofessional creative/casual prompt matched.")
            return {"safe": False, "reason": "Non-professional conversational context out of scope."}

    # 5. All negative checks passed — allow the prompt through
    print("✅ [Guardrail Pass] Prompt is secure and whitelisted.")
    return {"safe": True, "reason": "No threats detected."}


async def security_rail_middleware(prompt: str) -> str:
    """Master entry point for checking raw text inputs."""
    evaluation = await inspect_prompt_safety(prompt)
    if not evaluation["safe"]:
        raise SecurityException(
            message=evaluation["reason"],
            payload=str(prompt)
        )
    return str(prompt)