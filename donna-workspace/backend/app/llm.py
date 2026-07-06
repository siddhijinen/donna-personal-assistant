import os
from google import genai

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key or api_key == "your-gemini-api-key":
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=api_key)
    return _client


async def ask_gemini(prompt: str, system: str = "") -> str:
    """Send a prompt to Gemini 2.0 Flash and return the text response."""
    client = _get_client()
    contents = prompt
    config = None
    if system:
        config = genai.types.GenerateContentConfig(system_instruction=system)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        return response.text.strip()
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            return "⚠️ Gemini API Quota Exceeded (Rate Limit). Please verify that the Generative Language API is enabled for your project, check your billing details, or try again in a minute."
        return f"⚠️ Gemini API Error: {err_str}"
