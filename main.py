from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ROOT
@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}

# ✅ NOTES ROUTE
@app.post("/api/generate-notes-from-text")
async def generate_notes(data: dict):
    text = data.get("text", "")

    # TEMP simple notes logic
    return {
        "title": "Generated Notes",
        "content": text[:500]
    }