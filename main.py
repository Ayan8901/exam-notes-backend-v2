from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import sys
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()


class TextInput(BaseModel):
    text:         str
    systemPrompt: str | None = None

@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}

@app.post("/api/generate-notes-from-text")
async def generate_notes(data: TextInput):
    text = data.text.strip()
    log(f"[NOTES] received text_len={len(text)}")

    if not text or len(text) < 30:
        return {
            "title":   "Cannot Extract",
            "content": "• Could not extract meaningful text.\n• Try a clearer image with visible text."
        }

    if not GROQ_API_KEY:
        log("[NOTES] GROQ_API_KEY missing")
        return fallback_notes(text)

    MAX_INPUT_CHARS = 9000
    if len(text) > MAX_INPUT_CHARS:
        log(f"[NOTES] truncating input from {len(text)} to {MAX_INPUT_CHARS} chars")
        text = text[:MAX_INPUT_CHARS]

    try:
        word_count   = len(text.split())
        # Reduced ~25%: fewer sections and fewer bullets per section than before.
        max_sections = 4 if word_count < 300 else 5 if word_count < 600 else 7
        bullets_per  = "3-4" if word_count < 300 else "4-5"

        prompt = f"""You are an expert exam notes generator for students preparing for exams.

Your job has TWO parts:

PART 1 — Generate a smart title:
- Read the ENTIRE text and create a short meaningful title (4-7 words max)
- Title should describe the MAIN TOPIC, not just copy the first words
- Example: "Photosynthesis: Light and Dark Reactions"

PART 2 — Generate CONCISE expert exam-ready notes:
- Read the ENTIRE text carefully from start to finish
- Do NOT just copy headings or phrases from the book as bullet points
- Each bullet must be a COMPLETE ANSWER — not a topic name or heading
- BAD bullet: "Calculating Variance and Standard Deviation"
- GOOD bullet: "Variance measures how far values spread from mean; calculated as average of squared differences"
- Combine what the book says WITH your own expert knowledge for complete exam answers
- Be concise: only the MOST important facts, formulas, definitions - skip minor details
- For math topics: write formulas using plain text only — e.g. "a^2 + b^2 = c^2" NOT "$a^2 + b^2 = c^2$"
- NEVER use LaTeX syntax — no $ signs, no \\frac, no \\sqrt, no \\cdot, no backslashes
- Write math naturally: use ^ for powers, / for fractions, sqrt() for roots
- Group related points under short section headings
- Section heading format: ALL CAPS, no bullet, e.g. "FORMULA" or "KEY THEOREM"
- Each bullet point starts with "• "
- {bullets_per} bullets per section MAXIMUM (no repetition, be selective)
- Up to {max_sections} sections MAXIMUM
- Each bullet max 18 words — complete and self-contained, but tight
- Prioritize ONLY: core definitions, key formulas, most important facts for exams
- Always write full definitions — never truncate mid-sentence
- If text is random gibberish with no educational value, respond with only: CANNOT_EXTRACT

Respond in this exact format:
TITLE: <your title here>
NOTES:
<SECTION HEADING>
• bullet
• bullet
<SECTION HEADING>
• bullet
• bullet

Text to convert:
{text}"""

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  1800,
                    "temperature": 0.2,
                    "reasoning_effort": "low",
                },
            )

        log(f"[NOTES] Groq status={response.status_code}")

        try:
            result = response.json()
        except Exception:
            log(f"[NOTES] Non-JSON response: {response.text[:500]}")
            return fallback_notes(text)

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown Groq error")
            log(f"[NOTES] Groq API error: {error_msg}")
            if "reasoning_effort" in error_msg:
                log("[NOTES] retrying without reasoning_effort param")
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        GROQ_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type":  "application/json",
                        },
                        json={
                            "model": "openai/gpt-oss-120b",
                            "messages":    [{"role": "user", "content": prompt}],
                            "max_tokens":  1800,
                            "temperature": 0.2,
                        },
                    )
                result = response.json()
                if "error" in result:
                    log(f"[NOTES] Retry also failed: {result['error']}")
                    return fallback_notes(text)
            else:
                return fallback_notes(text)

        if not result.get("choices"):
            log(f"[NOTES] Groq empty choices. Full response: {result}")
            return fallback_notes(text)

        choice = result["choices"][0]
        finish_reason = choice.get("finish_reason")
        usage = result.get("usage", {})
        message = choice.get("message", {})
        raw_response = (message.get("content") or "").strip()
        reasoning_field = message.get("reasoning", "") or ""

        log(f"[NOTES] finish_reason={finish_reason} usage={usage} "
            f"content_len={len(raw_response)} reasoning_len={len(reasoning_field)}")

        if not raw_response and reasoning_field:
            raw_response = reasoning_field.strip()

        if not raw_response:
            log(f"[NOTES] Truly empty response. finish_reason={finish_reason}")
            return fallback_notes(text)

        if "CANNOT_EXTRACT" in raw_response:
            return {
                "title":   "Cannot Extract",
                "content": "• Could not find meaningful educational content.\n• Try a clearer textbook image or paste text directly."
            }

        title = "Untitled Note"
        if "TITLE:" in raw_response:
            title_line = raw_response.split("TITLE:")[1].split("\n")[0].strip()
            if title_line:
                title = title_line

        content = raw_response
        if "NOTES:" in raw_response:
            content = raw_response.split("NOTES:")[1].strip()

        log(f"[NOTES] Success. title={title!r} content_len={len(content)}")
        return {"title": title, "content": content}

    except Exception as e:
        log(f"[NOTES EXCEPTION] {type(e).__name__}: {e}")
        return fallback_notes(text)


def fallback_notes(text: str) -> dict:
    log("[NOTES] Using fallback_notes()")
    words     = text.split()
    title     = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullets   = []
    for sentence in sentences:
        sentence = sentence.strip().strip(".")
        if len(sentence) > 20:
            bullets.append(f"• {sentence}")
        if len(bullets) >= 8:
            break
    if not bullets:
        bullets = ["• Could not extract meaningful content. Try a clearer image."]
    return {"title": title, "content": "\n".join(bullets)}
