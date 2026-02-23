from fastapi import APIRouter, UploadFile, File
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from PIL import Image
import tempfile
import io
import os

# ✅ router (NOT app)
router = APIRouter()

# ✅ LOAD OCR MODEL ON START
print("Loading HEAVY OCR model (this takes time)...")
model = ocr_predictor(pretrained=True)
print("OCR model ready.")

# ✅ OCR ROUTE
@router.post("/ocr")
async def ocr_images(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # convert to PIL
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")

        # save temp image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            pil_image.save(tmp.name)
            temp_path = tmp.name

        # doctr OCR
        doc = DocumentFile.from_images([temp_path])
        result = model(doc)

        text = result.render()

        os.remove(temp_path)

        return {"success": True, "text": text}

    except Exception as e:
        print("OCR ERROR:", e)
        return {"success": False, "error": str(e)}