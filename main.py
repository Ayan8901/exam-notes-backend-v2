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

    if not text:
        return {"title": "Empty Note", "content": "• No text provided."}

    # Smart title from first 6 words
    words = text.split()
    title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

    # If no Groq key, fall back to simple bullet logic
    if not GROQ_API_KEY:
        return fallback_notes(title, text)

    try:
        prompt = f"""You are an expert exam notes generator for students.

Convert the following text into clear, concise exam-ready bullet notes.

Rules:
- Each bullet must start with "• "
- Maximum 15 bullets
- Each bullet should be one clear fact or concept
- Remove filler words, keep only key information
- Do not add any intro or outro text, just the bullets

Text:
{text}"""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       "llama-3.1-8b-instant",
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  1024,
                    "temperature": 0.3,
                },
            )

        result  = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        return {"title": title, "content": content}

    except Exception as e:
        # If Groq fails for any reason, fall back to simple logic
        print(f"Groq error: {e}")
        return fallback_notes(title, text)


def fallback_notes(title: str, text: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullets   = []
    for sentence in sentences:
        sentence = sentence.strip().strip(".")
        if len(sentence) > 20:
            bullets.append(f"• {sentence}")
        if len(bullets) >= 15:
            break
    if not bullets:
        bullets = [f"• {text[:300]}"]
    return {"title": title, "content": "\n".join(bullets)}
