from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # Split text into sentences and convert to bullets
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullets = []

    for sentence in sentences:
        sentence = sentence.strip().strip(".")
        if len(sentence) > 20:
            bullets.append(f"• {sentence}")
        if len(bullets) >= 20:
            break

    # Fallback if no sentences found
    if not bullets:
        chunks = [text[i:i+100] for i in range(0, min(len(text), 500), 100)]
        bullets = [f"• {chunk.strip()}" for chunk in chunks if chunk.strip()]

    return {
        "title": title,
        "content": "\n".join(bullets)
    }
