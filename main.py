from fastapi import FastAPI, UploadFile, File
from doctr.models import ocr_predictor
from PIL import Image
import io

app = FastAPI(title="OCR Backend")

# Load Doctr OCR model
predictor = ocr_predictor(pretrained=True)

@app.post("/ocr")
async def do_ocr(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    result = predictor([image])
    # Convert result to simple text list
    output = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                output.append(line.text)
    return {"text": "\n".join(output)}
