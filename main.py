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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

class TextInput(BaseModel):
    text: str

@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}

@app.post("/api/generate-notes-from-text")
async def generate_notes(data: TextInput):
    text = data.text.strip()

    if not text or len(text) < 30:
        return {
            "title": "Cannot Extract",
            "content": "• Could not extract meaningful text.\n• Try a clearer image with visible text."
        }

    if not GROQ_API_KEY:
        return fallback_notes(text)

    try:
        prompt = f"""You are an expert exam notes generator for students.

Your job has TWO parts:

PART 1 — Generate a smart title:
- Read the text and create a short meaningful title (4-7 words max)
- Title should describe the topic, NOT just copy the first words
- Example: "Photosynthesis: Light and Dark Reactions" not "Photosynthesis is a biological..."

PART 2 — Generate exam-ready bullet notes:
- Group related points under short section headings
- Section heading format: use ALL CAPS, no bullet, e.g. "DEFINITION" or "KEY STAGES"
- Each bullet point starts with "• "
- Maximum 3-4 bullets per section
- Maximum 4 sections total
- Each bullet max 15 words, no filler words
- Only include exam-worthy facts
- If text is random, gibberish, or has no educational value, respond with only: CANNOT_EXTRACT

Respond in this exact format:
TITLE: <your title here>
NOTES:
<section heading>
• bullet
• bullet
<section heading>
• bullet
• bullet

Text to convert:
{text}"""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       "llama-3.3-70b-versatile",  # upgraded model
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  1024,
                    "temperature": 0.2,
                },
            )

        result       = response.json()
        raw_response = result["choices"][0]["message"]["content"].strip()

        # Handle gibberish/out-of-context images
        if "CANNOT_EXTRACT" in raw_response:
            return {
                "title": "Cannot Extract",
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
        print(f"Groq error: {e}")
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
