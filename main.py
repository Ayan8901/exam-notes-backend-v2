from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from PIL import Image
import tempfile
import io
import os

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

# ✅ LOAD OCR MODEL
print("Loading OCR model...")
model = ocr_predictor(pretrained=True)
print("OCR ready")

# ✅ OCR ROUTE
@app.post("/ocr")
async def ocr_images(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            pil_image.save(tmp.name)
            temp_path = tmp.name

        doc = DocumentFile.from_images([temp_path])
        result = model(doc)
        text = result.render()

        os.remove(temp_path)

        return {"success": True, "text": text}

    except Exception as e:
        return {"success": False, "error": str(e)}

# ✅ NOTES ROUTE (TEMP MOCK)
@app.post("/api/generate-notes-from-text")
async def generate_notes(data: dict):
    text = data.get("text", "")

    # TEMP simple notes logic
    return {
        "title": "Generated Notes",
        "content": text[:500]
    }