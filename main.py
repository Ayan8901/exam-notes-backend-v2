from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-3.6-flash"
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/interactions"

class TextInput(BaseModel):
    text:         str
    systemPrompt: str | None = None


def extract_model_output_text(result: dict) -> str:
    collected = []
    steps = result.get("steps", [])
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("type") == "model_output":
            for part in step.get("content", []):
                if isinstance(part, dict) and part.get("type") == "text":
                    collected.append(part.get("text", ""))
    if collected:
        return "".join(collected)

    if result.get("output_text"):
        return result["output_text"]

    output = result.get("output", [])
    for item in output:
        if isinstance(item, dict):
            if "text" in item:
                collected.append(item["text"])
            elif "content" in item:
                for part in item.get("content", []):
                    if isinstance(part, dict) and "text" in part:
                        collected.append(part["text"])
    return "".join(collected)


@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}

@app.post("/api/generate-notes-from-text")
async def generate_notes(data: TextInput):
    text = data.text.strip()

    if not text or len(text) < 30:
        return {
            "title":   "Cannot Extract",
            "content": "• Could not extract meaningful text.\n• Try a clearer image with visible text."
        }

    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not set in environment variables")
        return fallback_notes(text)

    try:
        word_count   = len(text.split())
        max_sections = 5 if word_count < 300 else 7 if word_count < 600 else 10
        bullets_per  = "4-5" if word_count < 300 else "5-6"

        prompt = f"""You are an expert exam notes generator for students preparing for exams.

Your job has TWO parts:

PART 1 — Generate a smart title:
- Read the ENTIRE text and create a short meaningful title (4-7 words max)
- Title should describe the MAIN TOPIC, not just copy the first words
- Example: "Photosynthesis: Light and Dark Reactions"

PART 2 — Generate expert exam-ready notes:
- Read the ENTIRE text carefully from start to finish
- Do NOT just copy headings or phrases from the book as bullet points
- Each bullet must be a COMPLETE ANSWER — not a topic name or heading
- BAD bullet: "Calculating Variance and Standard Deviation"
- GOOD bullet: "Variance measures how far values spread from mean; calculated as average of squared differences"
- BAD bullet: "Interpreting Results"
- GOOD bullet: "Higher variance = more spread out data; lower variance = data clustered close to mean"
- Combine what the book says WITH your own expert knowledge for complete exam answers
- Add key facts, formulas, definitions even if not fully explained in the text
- For math topics: write formulas using plain text only — e.g. "a^2 + b^2 = c^2" NOT "$a^2 + b^2 = c^2$"
- NEVER use LaTeX syntax — no $ signs, no \\frac, no \\sqrt, no \\cdot, no backslashes
- Write math naturally: use ^ for powers, / for fractions, sqrt() for roots
- Group related points under short section headings
- Section heading format: ALL CAPS, no bullet, e.g. "FORMULA" or "KEY THEOREM"
- Each bullet point starts with "• "
- {bullets_per} bullets per section (no repetition)
- Up to {max_sections} sections maximum
- Each bullet max 25 words — complete and self-contained
- Prioritize: definitions, formulas, causes/effects, processes, key facts for exams
- Always write full definitions — never truncate mid-sentence
- If text is random gibberish with no educational value, respond with only: CANNOT_EXTRACT

Respond in this exact format:
TITLE: <your title here>
NOTES:
<SECTION HEADING>
• bullet
• bullet
• bullet
<SECTION HEADING>
• bullet
• bullet

Text to convert:
{text}"""

        payload = {
            "model": GEMINI_MODEL,
            "input": [
                {"type": "text", "text": prompt},
            ],
            "generation_config": {
                "temperature": 0.2,
                "max_output_tokens": 2048,
                "thinking_level": "low",
            },
        }

        headers = {
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(GEMINI_URL, headers=headers, json=payload)

        try:
            result = response.json()
        except Exception:
            print(f"Gemini non-JSON response (status {response.status_code}): {response.text[:300]}")
            return fallback_notes(text)

        if response.status_code != 200 or (isinstance(result, dict) and "error" in result):
            error_obj = result.get("error", {}) if isinstance(result, dict) else {}
            error_msg = error_obj.get("message", f"Gemini error (status {response.status_code}): {result}")
            print(f"Gemini API error: {error_msg}")
            return fallback_notes(text)

        raw_response = extract_model_output_text(result).strip()

        if not raw_response:
            print(f"Gemini empty text. Full response keys: {list(result.keys())}")
            return fallback_notes(text)

        if "CANNOT_EXTRACT" in raw_response:
            return {
                "title":   "Cannot Extract",
                "content": "• Could not find meaningful educational content.\n• Try a clearer textbook image or paste text directly."
            }

        # Parse title
        title = "Untitled Note"
        if "TITLE:" in raw_response:
            title_line = raw_response.split("TITLE:")[1].split("\n")[0].strip()
            if title_line:
                title = title_line

        # Parse notes content
        content = raw_response
        if "NOTES:" in raw_response:
            content = raw_response.split("NOTES:")[1].strip()

        return {"title": title, "content": content}

    except Exception as e:
        print(f"Gemini error: {e}")
        return fallback_notes(text)


def fallback_notes(text: str) -> dict:
    words     = text.split()
    title     = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullets   = []
    for sentence in sentences:
        sentence = sentence.strip().strip(".")
        if len(sentence) > 20:
            bullets.append(f"• {sentence}")
        if len(bullets) >= 10:
            break
    if not bullets:
        bullets = ["• Could not extract meaningful content. Try a clearer image."]
    return {"title": title, "content": "\n".join(bullets)}
