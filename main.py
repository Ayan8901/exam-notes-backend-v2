import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = "facebook/bart-large-cnn"

app = FastAPI()

class NotesRequest(BaseModel):
    text: str


@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}


@app.post("/generate-notes")
def generate_notes(req: NotesRequest):
    if not req.text or len(req.text.strip()) < 30:
        raise HTTPException(status_code=400, detail="Text too short")

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    payload = {
        "inputs": req.text,
        "parameters": {
            "max_length": 200,
            "min_length": 60
        }
    }

    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=60
        )

        data = r.json()

        if isinstance(data, dict) and data.get("error"):
            raise HTTPException(status_code=500, detail=data["error"])

        summary = data[0]["summary_text"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Convert summary → bullet notes
    bullets = summary.replace(". ", ".\n• ")
    notes = "• " + bullets

    return {
        "notes": notes
    }
